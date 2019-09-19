# install postgres and postgis
# create iftdss_s with postgis template
# import the data:
# c:\"program files"\postgresql\11\bin\psql iftdss_s < c:\_\ftem\2019-07-16\ftemprod.backup postgres
# "C:\bin\QGIS 3.4\bin\ogr2ogr" -f "PostgreSQL" "PG:host=127.0.0.1 user=postgres dbname=iftdss_s password=pg" "C:/_/ftem/2019-07-16/file_geodatabases/Wildfire_Poly.shp" -lco SCHEMA=ftem -lco GEOMETRY_NAME=the_geom -lco FID=gid -lco PRECISION=no -nlt PROMOTE_TO_MULTI -nln Wildfire_Poly -overwrite
# "C:\bin\QGIS 3.4\bin\ogr2ogr" -f "PostgreSQL" "PG:host=127.0.0.1 user=postgres dbname=iftdss_s password=pg" "C:/_/ftem/2019-07-16/file_geodatabases/Wildfire_Point.shp" -lco SCHEMA=ftem -lco GEOMETRY_NAME=the_geom -lco FID=gid -lco PRECISION=no -nlt PROMOTE_TO_MULTI -nln Wildfire_Point -overwrite
# "C:\bin\QGIS 3.4\bin\ogr2ogr" -f "PostgreSQL" "PG:host=127.0.0.1 user=postgres dbname=iftdss_s password=pg" "C:/_/ftem/2019-07-16/file_geodatabases/Treatment_Poly.shp" -lco SCHEMA=ftem -lco GEOMETRY_NAME=the_geom -lco FID=gid -lco PRECISION=no -nlt PROMOTE_TO_MULTI -nln Treatment_Poly -overwrite
# "C:\bin\QGIS 3.4\bin\ogr2ogr" -f "PostgreSQL" "PG:host=127.0.0.1 user=postgres dbname=iftdss_s password=pg" "C:/_/ftem/2019-07-16/file_geodatabases/Treatment_Point.shp" -lco SCHEMA=ftem -lco GEOMETRY_NAME=the_geom -lco FID=gid -lco PRECISION=no -nlt PROMOTE_TO_MULTI -nln Treatment_Point -overwrite

# c:\bin\python37-64\python c:\_\ftem\ftem.py
# c:\bin\python37-64\Scripts\pylint c:\_\ftem\ftem.py > c:\_\ftem\ftem.lint.txt

import os
import math
import datetime
import json
import psycopg2
import geopandas as gpd
import pandas as pd
import pandas.io.sql as psql
import numpy as np
import matplotlib.pyplot as plt
import django
from django.conf import settings
from django.template.loader import get_template
from django.utils.text import slugify
from shapely import geometry
from _topojson import topojson

settings.configure(
    DEBUG=False,
    TEMPLATES=[
        {
            'BACKEND': 'django.template.backends.django.DjangoTemplates',
            'DIRS': ['c:\\_\\ftem\\'],
            'APP_DIRS': False,
        },
    ])
django.setup()

#init(autoreset=True)

base_dir = 'C:\\_\\ftem\\'
now = datetime.datetime.now().strftime('%Y%m%d_%H%M')
#wp = gpd.read_file("C:\\_\\ftem\\2019-07-16\\file_geodatabases\\Wildfire_Poly.shp")

def cast_to_multigeometry(geom):
    upcast_dispatch = {geometry.Point: geometry.MultiPoint,
                       geometry.LineString: geometry.MultiLineString,
                       geometry.Polygon: geometry.MultiPolygon}
    caster = upcast_dispatch.get(type(geom), lambda x: x[0])
    return caster([geom])

def acres_to_buffer_radius(row):
    if row.daily_acres is not None:
        r = math.sqrt((1.5*row.daily_acres*4046.85642)/(math.pi))*2
    else:
        r = 10
    return r

def distance_buffer(row):
    r = row.buffer_radius
    return row.the_geom.buffer(r)

def distance_buffer2(row):
    r = row.buffer_radius
    return row.geometry.buffer(r)

def geojson_topojson(ageojson, atopojson):
    topojson(ageojson, atopojson, quantization=1e6, simplify=0.0001)

def csv_json(acsv, ajson):
    inr = pd.read_csv(acsv, sep=',')
    topbit = '[\n'
    with open(ajson, 'a') as outfile:
        outfile.write(topbit)
    pkey = 1
    for i, row in inr.iterrows():
        comma = ',\n'
        if pkey == 1:
            comma = ''
        pkey = pkey + 1
        created = '2019-09-18T00:00:00Z'
        fields = '{\n        "geom": "' + str(row['wpoly_geom']) + '",\n        "incident_name": "' + str(row['incident_name']) + '",\n        "irwin_id": "' + str(slugify(row['wpoly_irwin_id'])) + '",\n        "treatment_category": "' + str(row['treatment_category']) + '",\n        "treatment_type": "' + str(row['treatment_type']) + '",\n        "created": "' + str(row['date_added']) + '",\n        "modified": null,\n        "author": "' + str(row['added_by']) + '"\n    }\n'
        record = comma + '{\n    "model": "ftem.wtfull",\n    "pk": '+ str(pkey) + ',\n    "fields": ' + fields + '}'
        with open(ajson, 'a') as outfile:
            outfile.write(record)
    endbit = '\n]'
    with open(ajson, 'a') as outfile:
        outfile.write(endbit)

def dict_sweep(input_dict, key):
    if isinstance(input_dict, dict):
        return {k: dict_sweep(v, key) for k, v in input_dict.items() if k != key}
    elif isinstance(input_dict, list):
        return [dict_sweep(element, key) for element in input_dict]
    else:
        return input_dict

c = psycopg2.connect(database="iftdss_s", user="postgres", password="pg", host="127.0.0.1")

def main():
    #wildfire_points_year(2018)
    #wildfire_polys_year(2018)
    #wildfire_geoms_year(2018)
    wildfire_treatments_year(2018)
    wildfire_over_treatments_year(2018)

def wildfire_points_year(year):
    year_dir = base_dir + str(year) + '\\'
    if not os.path.exists(year_dir):
        os.makedirs(year_dir)
    sql = "select wp.*, w.* from ftem.wildfire_point wp left join ftem.wildfire w on wp.irwin_id = w.irwin_id where extract(year from w.start_date_time) = " + str(year) # count 22746 x 28 cols
    wildfire_points = gpd.GeoDataFrame.from_postgis(sql, c, geom_col='the_geom')
    wildfire_points.crs = {'init': 'epsg:4269'}
    wildfire_points = wildfire_points.to_crs({'init': 'epsg:2163'})
    wildfire_points['start_date_time'] = wildfire_points['start_date_time'].dt.to_pydatetime().astype(str)
    wildfire_points['containment_date_time'] = wildfire_points['containment_date_time'].dt.to_pydatetime().astype(str)
    wildfire_points['control_date_time'] = wildfire_points['control_date_time'].dt.to_pydatetime().astype(str)
    wildfire_points['out_date_time'] = wildfire_points['out_date_time'].dt.to_pydatetime().astype(str)
    wildfire_points['geomac_date_current'] = wildfire_points['geomac_date_current'].dt.to_pydatetime().astype(str)
    wildfire_points['min_date_time'] = wildfire_points['min_date_time'].dt.to_pydatetime().astype(str)
    wildfire_points.to_file(driver='ESRI Shapefile', filename=year_dir + 'wildfire_points.shp')
    wildfire_points_buffer = wildfire_points.copy()
    wildfire_points_buffer['buffer_radius'] = wildfire_points_buffer.apply(acres_to_buffer_radius, axis=1)
    wildfire_points_buffer['the_geom'] = wildfire_points_buffer.apply(distance_buffer, axis=1)
    wildfire_points_buffer.to_file(driver='ESRI Shapefile', filename=year_dir + 'wildfire_points_buffer.shp')

def wildfire_polys_year(year):
    year_dir = base_dir + str(year) + '\\'
    if not os.path.exists(year_dir):
        os.makedirs(year_dir)
    sql = "select wp.*, w.* from ftem.wildfire_poly wp left join ftem.wildfire w on wp.irwin_id = w.irwin_id where extract(year from w.start_date_time) = " + str(year) # count 1373 x 30 cols
    wildfire_polys = gpd.GeoDataFrame.from_postgis(sql, c, geom_col='the_geom')
    wildfire_polys.crs = {'init': 'epsg:4269'}
    wildfire_polys = wildfire_polys.to_crs({'init': 'epsg:2163'})
    wildfire_polys = wildfire_polys.drop(columns=['st_area_sh', 'st_length_'])
    wildfire_polys['start_date_time'] = wildfire_polys['start_date_time'].dt.to_pydatetime().astype(str)
    wildfire_polys['containment_date_time'] = wildfire_polys['containment_date_time'].dt.to_pydatetime().astype(str)
    wildfire_polys['control_date_time'] = wildfire_polys['control_date_time'].dt.to_pydatetime().astype(str)
    wildfire_polys['out_date_time'] = wildfire_polys['out_date_time'].dt.to_pydatetime().astype(str)
    wildfire_polys['geomac_date_current'] = wildfire_polys['geomac_date_current'].dt.to_pydatetime().astype(str)
    wildfire_polys['min_date_time'] = wildfire_polys['min_date_time'].dt.to_pydatetime().astype(str)
    wildfire_polys.to_file(driver='ESRI Shapefile', filename=year_dir + 'wildfire_polys.shp')
    wildfire_polys_buffer = wildfire_polys.copy()
    wildfire_polys_buffer['buffer_radius'] = 1
    wildfire_polys_buffer['the_geom'] = wildfire_polys_buffer.apply(distance_buffer, axis=1)
    wildfire_polys_buffer.to_file(driver='ESRI Shapefile', filename=year_dir + 'wildfire_polys_buffer.shp')

def wildfire_geoms_year(year):
    year_dir = base_dir + str(year) + '\\'
    if not os.path.exists(year_dir):
        os.makedirs(year_dir)
    sql = "select wp.*, w.* from ftem.wildfire_point wp left join ftem.wildfire w on wp.irwin_id = w.irwin_id where extract(year from w.start_date_time) = " + str(year) # count 22746 x 28 cols
    wildfire_points = gpd.GeoDataFrame.from_postgis(sql, c, geom_col='the_geom')
    wildfire_points.crs = {'init': 'epsg:4269'}
    sql = "select wp.*, w.* from ftem.wildfire_poly wp left join ftem.wildfire w on wp.irwin_id = w.irwin_id where extract(year from w.start_date_time) = " + str(year)
    wildfire_polys = gpd.GeoDataFrame.from_postgis(sql, c, geom_col='the_geom')
    wildfire_polys.crs = {'init': 'epsg:4269'}

    #wpdf1 = wpdf1.drop(columns=['st_area_sh','st_length_','gid','ftem_wildf'])

    #wpdf = gpd.concat([wpdf1,wpdf2]).drop_duplicates('irwin_id')
    wildfire_geoms = wildfire_points.copy()
    wildfire_geoms.set_index('irwin_id', inplace=True)
    wildfire_polys.set_index('irwin_id', inplace=True)
    #print(wildfire_geoms.columns)
    #print(wildfire_polys.columns)

    wildfire_geoms.update(wildfire_polys) # 21373 point + 1373 poly
    #print(wildfire_geoms)
    extra_cols = [e for e in wildfire_geoms.columns if e not in ['ftem_wildf', 'unique_fire_identifier', 'incident_name', 'the_geom']]
    renames = {'ftem_wildf': 'f', 'unique_fire_identifier': 'u', 'incident_name': 'i'}
    wildfire_geoms = wildfire_geoms.drop(columns=extra_cols).rename(index=str, columns=renames)
    #wildfire_points.to_file(driver='ESRI Shapefile', filename=base_dir + 'wildfire_points_polys.shp')
    #extra_cols = [e for e in wildfire_points.columns if e not in ['unique_fire_identifier', 'incident_name']]
    #renames = {'unique_fire_identifier': 'u', 'incident_name': 'i'}
    #wildfire_pd = wildfire_geoms#.drop(columns=extra_cols)
    out_geojson = year_dir + 'wildfire_geoms-' + now +'.json'
    out_topojson = year_dir + 'wildfire_geoms-' + now +'.json.packed'
    #wildfire_pd = pd.DataFrame(wildfire_pd)
    #wildfire_pd.to_json(path_or_buf=out_geojson, orient='records')
    #wildfire_geoms.to_csv(base_dir + 'testgeoms.csv')
    wildfire_geoms.to_file(out_geojson, driver="GeoJSON")
    geojson_topojson(out_geojson, out_topojson)
    os.remove(out_geojson)

def wildfire_treatments_year(year):
    year_dir = base_dir + str(year) + '\\'
    if not os.path.exists(year_dir):
        os.makedirs(year_dir)
    sql = "select wt.ftem_wildfire_id, wt.ftem_treatment_id, wt.definite_interaction, wt.added_by, wt.date_added, wt.status, wt.acres_burned, wt.agency as wt_agency, wt.gis_type as wt_gis_type,t.treatment_id,t.map_method, t.date_current, t.comments, t.treatment_identifier_database, t.treatment_name, t.treatment_category, t.treatment_type, t.actual_completion_date, t.treatment_acres, t.treatment_status, t.gis_id, t.suid, t.sub_unit, t.agency as t_agency, t.region, t.admin_forest_code, t.org, t.activity_code, t.activity, t.state, t.ownership, t.keypoint, t.fund_code, t.nepa_doc_name, t.implement_proj, t.f_treatment_name, t.unit_name, t.jupiter_status, t.fiscal_year, t.actual_initiation_date, t.geometry_id, t.project_name, t.gis_acres, t.gis_type as t_gis_type, t.bbox_west_long as t_bbox_west_long, t.bbox_east_long as t_bbox_east_long, t.bbox_north_lat as t_bbox_north_lat, t.bbox_south_lat as t_bbox_south_lat, t.last_updated, t.latitude, t.longitude, t.ui_treatment_id, w.unique_fire_identifier, w.irwin_id, w.incident_name, w.start_date_time, w.containment_date_time, w.control_date_time, w.out_date_time, w.poo_latitude, w.poo_longitude, w.poo_landowner_category, w.poo_protecting_agency, w.multi_jurisdictional, w.bbox_west_long as w_bbox_west_long, w.bbox_east_long as w_bbox_east_long, w.bbox_north_lat as w_bbox_north_lat, w.bbox_south_lat as w_bbox_south_lat, w.daily_acres, w.fire_cause, w.geomac_date_current, w.perimeter_acres, w.min_date_time, w.poo_jurisdictional_unit, w.interactions, qr.question_id, qr.response, qr.user_id, qr.entry_time, q.id as q_id, q.question, q.question_type, q.sub_type, q.mandatory, q.disabled, q.agency as q_agency, q.group_id, q.pres_order, q.supports, q.min_value, q.max_value, q.list_id, q.batch, q.question_short, q.report_order, q.report_value, qg.id as qg_id, qg.header, qg.init_expand_default, qg.sequence, tgeom.gid as tgeom_gid, tgeom.ftem_treat, tgeom.unique_tre, tgeom.the_geom as geometry from ftem.wildfire_treatments wt left join ftem.treatment t on (wt.ftem_treatment_id = t.ftem_treatment_id) left join ftem.wildfire w on (wt.ftem_wildfire_id = w.ftem_wildfire_id) left join ftem.question_response qr on (qr.ftem_treatment_id = t.ftem_treatment_id and qr.ftem_wildfire_id = w.ftem_wildfire_id) left join ftem.question q on (q.id = qr.question_id) left join ftem.question_group qg on (q.group_id = qg.id) left join ftem.treatment_point tgeom on (wt.ftem_treatment_id = tgeom.ftem_treat) where extract(year from w.start_date_time) = " + str(year) + " and wt.gis_type = 'point' and t.gis_type = 'point'" # 1744 rows x 104 columns]
    #wildfire_treatments_point = psql.read_sql_query(sql, con=c)
    wildfire_treatments_point = gpd.GeoDataFrame.from_postgis(sql, c, geom_col='geometry')

    sql = "select wt.ftem_wildfire_id, wt.ftem_treatment_id, wt.definite_interaction, wt.added_by, wt.date_added, wt.status, wt.acres_burned, wt.agency as wt_agency, wt.gis_type as wt_gis_type,t.treatment_id,t.map_method, t.date_current, t.comments, t.treatment_identifier_database, t.treatment_name, t.treatment_category, t.treatment_type, t.actual_completion_date, t.treatment_acres, t.treatment_status, t.gis_id, t.suid, t.sub_unit, t.agency as t_agency, t.region, t.admin_forest_code, t.org, t.activity_code, t.activity, t.state, t.ownership, t.keypoint, t.fund_code, t.nepa_doc_name, t.implement_proj, t.f_treatment_name, t.unit_name, t.jupiter_status, t.fiscal_year, t.actual_initiation_date, t.geometry_id, t.project_name, t.gis_acres, t.gis_type as t_gis_type, t.bbox_west_long as t_bbox_west_long, t.bbox_east_long as t_bbox_east_long, t.bbox_north_lat as t_bbox_north_lat, t.bbox_south_lat as t_bbox_south_lat, t.last_updated, t.latitude, t.longitude, t.ui_treatment_id, w.unique_fire_identifier, w.irwin_id, w.incident_name, w.start_date_time, w.containment_date_time, w.control_date_time, w.out_date_time, w.poo_latitude, w.poo_longitude, w.poo_landowner_category, w.poo_protecting_agency, w.multi_jurisdictional, w.bbox_west_long as w_bbox_west_long, w.bbox_east_long as w_bbox_east_long, w.bbox_north_lat as w_bbox_north_lat, w.bbox_south_lat as w_bbox_south_lat, w.daily_acres, w.fire_cause, w.geomac_date_current, w.perimeter_acres, w.min_date_time, w.poo_jurisdictional_unit, w.interactions, qr.question_id, qr.response, qr.user_id, qr.entry_time, q.id as q_id, q.question, q.question_type, q.sub_type, q.mandatory, q.disabled, q.agency as q_agency, q.group_id, q.pres_order, q.supports, q.min_value, q.max_value, q.list_id, q.batch, q.question_short, q.report_order, q.report_value, qg.id as qg_id, qg.header, qg.init_expand_default, qg.sequence, tgeom.gid as tgeom_gid, tgeom.ftem_treat, tgeom.unique_tre, tgeom.the_geom as geometry from ftem.wildfire_treatments wt left join ftem.treatment t on (wt.ftem_treatment_id = t.ftem_treatment_id) left join ftem.wildfire w on (wt.ftem_wildfire_id = w.ftem_wildfire_id) left join ftem.question_response qr on (qr.ftem_treatment_id = t.ftem_treatment_id and qr.ftem_wildfire_id = w.ftem_wildfire_id) left join ftem.question q on (q.id = qr.question_id) left join ftem.question_group qg on (q.group_id = qg.id) left join ftem.treatment_poly tgeom on (wt.ftem_treatment_id = tgeom.ftem_treat) where extract(year from w.start_date_time) = " + str(year) + " and wt.gis_type = 'poly' and t.gis_type = 'poly'" # 29445 rows x 104 columns]
    #wildfire_treatments_poly = psql.read_sql_query(sql, con=c)
    wildfire_treatments_poly = gpd.GeoDataFrame.from_postgis(sql, c, geom_col='geometry')

    crs = {'init': 'epsg:4269'}
    wt = pd.concat([wildfire_treatments_point, wildfire_treatments_poly], ignore_index=True)
    #print(len(wt))
    #tgeom = wt['tgeom_geom']
    #wt = wt[wt.tgeom_geom.notnull()]
    #print(len(wt))

    #print(wt.geometry)

    #for index, row in wt.iterrows():
        # it will throw an error where the geometry WKT isn't valid
    #    wt.set_value(index, 'geometry', loads(row['tgeom_geom']))

    wildfire_treatments = gpd.GeoDataFrame(wt, crs=crs)
    #extra_cols = [e for e in wildfire_treatments.columns if e not in ['ftem_treatment_id', 'geometry']]
    renames = {'ftem_wildfire_id': 'f'}
    wildfire_treatments = wildfire_treatments.rename(index=str, columns=renames)
    #wildfire_treatments.crs = {'init': 'epsg:4269'}
    #print(len(wildfire_treatments))

    #out_geojson = base_dir + 'wt.json'
    #wildfire_treatments.to_file(out_geojson, driver="GeoJSON")

    #wildfire_treatments = gpd.GeoDataFrame.from_postgis(sql, c, geom_col='tgeom_geom' )
    #extra_cols = [e for e in wildfire_treatments.columns if e not in ['irwin_id', 'incident_name', 'tpoly_geom']]
    #renames = {}
    #print(wildfire_geoms.columns)
    #print(wildfire_treatments.columns)

    #from shapely import wkb

    #wildfire_treatments['geometry'] = wildfire_treatments['geometry'].apply(wkb.loads)

    #wildfire_treatments.to_csv(base_dir +'wt.csv', index=False)

    #wildfire_treatments.to_file(driver='ESRI Shapefile', filename=base_dir + 'wr.shp')

    sql = "select wp.*, w.* from ftem.wildfire_point wp left join ftem.wildfire w on wp.irwin_id = w.irwin_id where extract(year from w.start_date_time) = " + str(year) # count 22746 x 28 cols
    wildfire_points = gpd.GeoDataFrame.from_postgis(sql, c, geom_col='the_geom')
    wildfire_points.crs = {'init': 'epsg:4269'}
    sql = "select wp.*, w.* from ftem.wildfire_poly wp left join ftem.wildfire w on wp.irwin_id = w.irwin_id where extract(year from w.start_date_time) = " + str(year)
    wildfire_polys = gpd.GeoDataFrame.from_postgis(sql, c, geom_col='the_geom')
    wildfire_polys.crs = {'init': 'epsg:4269'}

    #wpdf1 = wpdf1.drop(columns=['st_area_sh','st_length_','gid','ftem_wildf'])

    #wpdf = gpd.concat([wpdf1,wpdf2]).drop_duplicates('irwin_id')
    wildfire_geoms = wildfire_points.copy()
    wildfire_geoms.set_index('irwin_id', inplace=True)
    wildfire_polys.set_index('irwin_id', inplace=True)
    wildfire_geoms.update(wildfire_polys) # 21373 point + 1373 poly
    extra_cols = [e for e in wildfire_geoms.columns if e not in ['ftem_wildf', 'unique_fire_identifier', 'incident_name', 'the_geom']]
    renames = {'ftem_wildf': 'f', 'unique_fire_identifier': 'u', 'incident_name': 'i'}
    wildfire_geoms = wildfire_geoms.drop(columns=extra_cols).rename(index=str, columns=renames)
    wildfire_treatments = wildfire_geoms.merge(wildfire_treatments, on='f') # [49553 rows x 107 columns]
    #print(wildfire_treatments)

    #wt1 = wildfire_treatments[wildfire_treatments['f'] == 83027.0]
    #extra_cols = [e for e in wt1.columns if e not in ['f','ftem_treatment_id', 'unique_fire_identifier']]
    #renames = {}
    #print(len(wt1)) # treatment questions
    #wt1 = wt1.drop(columns=extra_cols).rename(index=str, columns=renames)
    #print(wt1) # unique treatments

    wtfs = wildfire_treatments['f'].value_counts()
    #print(wtfs)
    wtfs.to_csv(year_dir + 'wtfs.csv')
    #quit()
    #wildfire_treatments = wildfire_treatments.drop(columns=extra_cols).rename(index=str, columns=renames)

def wildfire_over_treatments_year(year):
    year_dir = base_dir + str(year) + '\\'
    if not os.path.exists(year_dir):
        os.makedirs(year_dir)

    sql = "select wp.*, w.* from ftem.wildfire_point wp left join ftem.wildfire w on wp.irwin_id = w.irwin_id where extract(year from w.start_date_time) = " + str(year) # count 22746 x 28 cols
    wildfire_points = gpd.GeoDataFrame.from_postgis(sql, c, geom_col='the_geom')
    wildfire_points.crs = {'init': 'epsg:4269'}
    wildfire_points = wildfire_points.to_crs({'init': 'epsg:2163'})

    wildfire_points['buffer_radius'] = wildfire_points.apply(acres_to_buffer_radius, axis=1)
    #wildfire_points_buffer['the_geom'] = wildfire_points_buffer.apply(distance_buffer, axis=1)

    sql = "select wp.*, w.* from ftem.wildfire_poly wp left join ftem.wildfire w on wp.irwin_id = w.irwin_id where extract(year from w.start_date_time) = " + str(year)
    wildfire_polys = gpd.GeoDataFrame.from_postgis(sql, c, geom_col='the_geom')
    wildfire_polys.crs = {'init': 'epsg:4269'}
    wildfire_polys = wildfire_polys.to_crs({'init': 'epsg:2163'})
    wildfire_polys['buffer_radius'] = 1

    #wpdf1 = wpdf1.drop(columns=['st_area_sh','st_length_','gid','ftem_wildf'])

    #wpdf = gpd.concat([wpdf1,wpdf2]).drop_duplicates('irwin_id')
    wildfire_geoms = wildfire_points.copy()
    wildfire_geoms.set_index('irwin_id', inplace=True)
    wildfire_polys.set_index('irwin_id', inplace=True)
    wildfire_geoms.update(wildfire_polys) # 21373 point + 1373 poly
    extra_cols = [e for e in wildfire_geoms.columns if e not in ['ftem_wildf', 'unique_fire_identifier', 'incident_name', 'daily_acres', 'buffer_radius', 'the_geom']]
    renames = {'ftem_wildf': 'f', 'unique_fire_identifier': 'u', 'incident_name': 'i'}
    wildfire_geoms = wildfire_geoms.drop(columns=extra_cols).rename(index=str, columns=renames)
    #wildfire_geoms = wildfire_geoms.to_crs({'init': 'epsg:2163'})

    sql = "select wt.ftem_wildfire_id, wt.ftem_treatment_id, wt.definite_interaction, wt.added_by, wt.date_added, wt.status, wt.acres_burned, wt.agency as wt_agency, wt.gis_type as wt_gis_type,t.treatment_id,t.map_method, t.date_current, t.comments, t.treatment_identifier_database, t.treatment_name, t.treatment_category, t.treatment_type, t.actual_completion_date, t.treatment_acres, t.treatment_status, t.gis_id, t.suid, t.sub_unit, t.agency as t_agency, t.region, t.admin_forest_code, t.org, t.activity_code, t.activity, t.state, t.ownership, t.keypoint, t.fund_code, t.nepa_doc_name, t.implement_proj, t.f_treatment_name, t.unit_name, t.jupiter_status, t.fiscal_year, t.actual_initiation_date, t.geometry_id, t.project_name, t.gis_acres, t.gis_type as t_gis_type, t.bbox_west_long as t_bbox_west_long, t.bbox_east_long as t_bbox_east_long, t.bbox_north_lat as t_bbox_north_lat, t.bbox_south_lat as t_bbox_south_lat, t.last_updated, t.latitude, t.longitude, t.ui_treatment_id, w.unique_fire_identifier, w.irwin_id, w.incident_name, w.start_date_time, w.containment_date_time, w.control_date_time, w.out_date_time, w.poo_latitude, w.poo_longitude, w.poo_landowner_category, w.poo_protecting_agency, w.multi_jurisdictional, w.bbox_west_long as w_bbox_west_long, w.bbox_east_long as w_bbox_east_long, w.bbox_north_lat as w_bbox_north_lat, w.bbox_south_lat as w_bbox_south_lat, w.daily_acres, w.fire_cause, w.geomac_date_current, w.perimeter_acres, w.min_date_time, w.poo_jurisdictional_unit, w.interactions, qr.question_id, qr.response, qr.user_id, qr.entry_time, q.id as q_id, q.question, q.question_type, q.sub_type, q.mandatory, q.disabled, q.agency as q_agency, q.group_id, q.pres_order, q.supports, q.min_value, q.max_value, q.list_id, q.batch, q.question_short, q.report_order, q.report_value, qg.id as qg_id, qg.header, qg.init_expand_default, qg.sequence, tgeom.gid as tgeom_gid, tgeom.ftem_treat, tgeom.unique_tre, tgeom.the_geom as geometry from ftem.wildfire_treatments wt left join ftem.treatment t on (wt.ftem_treatment_id = t.ftem_treatment_id) left join ftem.wildfire w on (wt.ftem_wildfire_id = w.ftem_wildfire_id) left join ftem.question_response qr on (qr.ftem_treatment_id = t.ftem_treatment_id and qr.ftem_wildfire_id = w.ftem_wildfire_id) left join ftem.question q on (q.id = qr.question_id) left join ftem.question_group qg on (q.group_id = qg.id) left join ftem.treatment_point tgeom on (wt.ftem_treatment_id = tgeom.ftem_treat) where extract(year from w.start_date_time) = " + str(year) + " and wt.gis_type = 'point' and t.gis_type = 'point'" # 1744 rows x 104 columns]
    #wildfire_treatments_point = psql.read_sql_query(sql, con=c)
    wildfire_treatments_point = gpd.GeoDataFrame.from_postgis(sql, c, geom_col='geometry')

    sql = "select wt.ftem_wildfire_id, wt.ftem_treatment_id, wt.definite_interaction, wt.added_by, wt.date_added, wt.status, wt.acres_burned, wt.agency as wt_agency, wt.gis_type as wt_gis_type,t.treatment_id,t.map_method, t.date_current, t.comments, t.treatment_identifier_database, t.treatment_name, t.treatment_category, t.treatment_type, t.actual_completion_date, t.treatment_acres, t.treatment_status, t.gis_id, t.suid, t.sub_unit, t.agency as t_agency, t.region, t.admin_forest_code, t.org, t.activity_code, t.activity, t.state, t.ownership, t.keypoint, t.fund_code, t.nepa_doc_name, t.implement_proj, t.f_treatment_name, t.unit_name, t.jupiter_status, t.fiscal_year, t.actual_initiation_date, t.geometry_id, t.project_name, t.gis_acres, t.gis_type as t_gis_type, t.bbox_west_long as t_bbox_west_long, t.bbox_east_long as t_bbox_east_long, t.bbox_north_lat as t_bbox_north_lat, t.bbox_south_lat as t_bbox_south_lat, t.last_updated, t.latitude, t.longitude, t.ui_treatment_id, w.unique_fire_identifier, w.irwin_id, w.incident_name, w.start_date_time, w.containment_date_time, w.control_date_time, w.out_date_time, w.poo_latitude, w.poo_longitude, w.poo_landowner_category, w.poo_protecting_agency, w.multi_jurisdictional, w.bbox_west_long as w_bbox_west_long, w.bbox_east_long as w_bbox_east_long, w.bbox_north_lat as w_bbox_north_lat, w.bbox_south_lat as w_bbox_south_lat, w.daily_acres, w.fire_cause, w.geomac_date_current, w.perimeter_acres, w.min_date_time, w.poo_jurisdictional_unit, w.interactions, qr.question_id, qr.response, qr.user_id, qr.entry_time, q.id as q_id, q.question, q.question_type, q.sub_type, q.mandatory, q.disabled, q.agency as q_agency, q.group_id, q.pres_order, q.supports, q.min_value, q.max_value, q.list_id, q.batch, q.question_short, q.report_order, q.report_value, qg.id as qg_id, qg.header, qg.init_expand_default, qg.sequence, tgeom.gid as tgeom_gid, tgeom.ftem_treat, tgeom.unique_tre, tgeom.the_geom as geometry from ftem.wildfire_treatments wt left join ftem.treatment t on (wt.ftem_treatment_id = t.ftem_treatment_id) left join ftem.wildfire w on (wt.ftem_wildfire_id = w.ftem_wildfire_id) left join ftem.question_response qr on (qr.ftem_treatment_id = t.ftem_treatment_id and qr.ftem_wildfire_id = w.ftem_wildfire_id) left join ftem.question q on (q.id = qr.question_id) left join ftem.question_group qg on (q.group_id = qg.id) left join ftem.treatment_poly tgeom on (wt.ftem_treatment_id = tgeom.ftem_treat) where extract(year from w.start_date_time) = " + str(year) + " and wt.gis_type = 'poly' and t.gis_type = 'poly'" # 29445 rows x 104 columns]
    #wildfire_treatments_poly = psql.read_sql_query(sql, con=c)
    wildfire_treatments_poly = gpd.GeoDataFrame.from_postgis(sql, c, geom_col='geometry')

    crs = {'init': 'epsg:4269'}
    wt = pd.concat([wildfire_treatments_point, wildfire_treatments_poly], ignore_index=True)
    #print(len(wt))
    #tgeom = wt['tgeom_geom']
    #wt = wt[wt.tgeom_geom.notnull()]
    #print(len(wt))

    #print(wt.geometry)

    #for index, row in wt.iterrows():
        # it will throw an error where the geometry WKT isn't valid
    #    wt.set_value(index, 'geometry', loads(row['tgeom_geom']))

    wildfire_treatments = gpd.GeoDataFrame(wt, crs=crs)
    #extra_cols = [e for e in wildfire_treatments.columns if e not in ['ftem_treatment_id', 'geometry']]
    renames = {'ftem_wildfire_id': 'f'}
    wildfire_treatments = wildfire_treatments.rename(index=str, columns=renames)

    wildfire_treatments = wildfire_geoms.merge(wildfire_treatments, on='f') # [49553 rows x 107 columns]

    #print(wildfire_geoms)
    ulist = wildfire_treatments['u'].drop_duplicates()
    #print(ulist.head)
    #print(len(ulist))
    #print(ulist)
    #uframe = pd.DataFrame(ulist, index=[0])
    uframe = ulist.to_frame()#.reset_index()
    #print(len(uframe))
    #print(uframe)
    #quit()
    #fire_year = ulist.applywildfire_geoms.
    #grazing_full = (grazing[grazing['ALLOTMENT_NUM'].isin(grazing_inside['ALLOTMENT_NUM'])])
    extra_cols = [e for e in wildfire_treatments.columns if e not in ['f', 'u', 'i', 'geometry']]
    renames = {}
    wtcut = wildfire_treatments.drop(columns=extra_cols).rename(index=str, columns=renames)

    wildfire_geom_buffer = wildfire_geoms.copy()
    wildfire_geom_buffer['the_geom'] = wildfire_geom_buffer.apply(distance_buffer, axis=1)
    wildfire_geom_buffer['the_geom'] = wildfire_geom_buffer.the_geom.apply(cast_to_multigeometry)
    extra_cols = [e for e in wildfire_geoms.columns if e not in ['u', 'i', 'daily_acres', 'the_geom']]
    renames = {'daily_acres': 'a', 'the_geom': 'geometry'}
    wcut = wildfire_geom_buffer.drop(columns=extra_cols).rename(index=str, columns=renames)
    #print(len(wcut))
    #print(wcut)

    #print(wcut.columns)
    #quit()

    #uframe['geometry'] = uframe['geometry'].apply(wtcut.geometry)
    #print(uframe.index)
    #print(uframe.index.dtype)
    #wtcut.set_index(wtcut.index.astype(int))
    #print(wcut.index)
    #print(wcut.index.dtype)

    #wcut.index = wcut.index.astype(int)
    #wcut = wcut.sort_index()
    #print(wtcut.index)
    #print(wtcut.index.dtype)
    fyear = uframe.merge(wcut, how="left", on='u')
    #fyear = uframe.merge(wcut, how="left", left_index=True, right_index=True)
    #fyear = uframe.join(wtcut, how="inner")
    #print(len(fyear))
    #print(fyear.head)
    ulv = fyear.values
    #print(ulv)
    #print(len(ulv))

    crs = {'init': 'epsg:2163'}
    fyear = gpd.GeoDataFrame(fyear, crs=crs)
    fyear = fyear.to_crs(epsg=4326) # EPSG:4269 - NAD83 - Geographic
    fyear.to_file(year_dir + 'data.json', driver="GeoJSON")
    geojson_topojson(year_dir + 'data.json', year_dir + 'data.json.packed')
    os.remove(year_dir + 'data.json')

    context = {'yyyy': year, 'wcount': len(ulv)}
    template = get_template("build_year.html")
    content = template.render(context)
    with open(year_dir + 'index.html', 'w') as static_file:
        static_file.write(content)
    template = get_template("build_year.js")
    content = template.render(context)
    with open(year_dir + 'data.js', 'w') as static_file:
        static_file.write(content)

    #quit()

    for wildfire in wildfire_geoms.itertuples():
        #test = wildfire_treatments[wildfire_treatments['f'].str.contains(wildfire[1])]
        test = wildfire[1] in wildfire_treatments['f'].values
        #print(test)
        #if test is True and wildfire[3] == '2018-SCFMF-000082':
        #if test is True and wildfire[3] == '2018-SCFMF-000082':
        #if test is True and wildfire[3] in ['2018-ORMED-000395']:
        if test is True and wildfire[3] in ['2018-CAMEU-008646', '2018-SCFMF-000002','2018-ORRSF-000354','2018-ORMED-000395']:
            print(wildfire)
            #wildfire_geom_buffer = wildfire_geoms.copy()
            #wildfire_geom_buffer['buffer_radius'] = wildfire_geom_buffer.apply(acres_to_buffer_radius, axis=1)
            #wildfire_geom_buffer['the_geom'] = wildfire_geom_buffer.apply(distance_buffer, axis=1)

        #if test is True:
            fire_dir = base_dir + str(year) + '\\' + wildfire[3] + '\\'
            if not os.path.exists(fire_dir):
                os.makedirs(fire_dir)
            out_geojson = fire_dir + 'data.json'
            out_topojson = fire_dir + 'data.json.packed'
            #print(wildfire)
            #print(getattr(wildfire, 'Index'), getattr(wildfire, 'u'))
            #print(context)
            #row = {'index' : getattr(wildfire, 'Index'), 'u' : getattr(wildfire, 'u'), 'i' : getattr(wildfire, 'i'), 'geometry': getattr(wildfire, 'the_geom')}
            #print(row)
            context = {'f': wildfire[1], 'u': wildfire[3], 'i': wildfire[4], 'a': wildfire[5], 'buffer_radius': wildfire[6]}
            #print(context)
            wildfire_df = pd.DataFrame(context, index=[0])
            wildfire_df['geometry'] = [wildfire[2]]
            #print(wildfire_df)
            wildfire_gdf = gpd.GeoDataFrame(wildfire_df)
            #print(wildfire_gdf)
            #wildfire_gdf.crs = {'init': 'epsg:4269'}
            wildfire_gdf.crs = {'init': 'epsg:2163'}
            #print(wildfire_gdf.crs)
            wildfire_buffer = wildfire_gdf.copy()
            wildfire_gdfc = wildfire_gdf.to_crs(epsg=4326) # EPSG:4269 - NAD83 - Geographic
            wildfire_gdfc = wildfire_gdfc.drop(columns=['buffer_radius'])
            wildfire_gdfc.to_file(out_geojson, driver="GeoJSON")
            #print(wildfire_gdfc.crs)
            geojson_topojson(out_geojson, out_topojson)
            os.remove(out_geojson)

            wildfire_buffer['geometry'] = wildfire_buffer.apply(distance_buffer2, axis=1)
            wildfire_buffer = wildfire_buffer.to_crs(epsg=4326) # EPSG:4269 - NAD83 - Geographic
            wildfire_buffer.to_file(fire_dir + 'datb.json', driver="GeoJSON")
            geojson_topojson(fire_dir + 'datb.json', fire_dir + 'datb.json.packed')
            os.remove(fire_dir + 'datb.json')

            wtq = wildfire_treatments[wildfire_treatments['f'] == wildfire[1]]
            #wtq = wildfire_treatments[wildfire_treatments['f']==83027.0]
            #print(wtq.columns)
            extra_cols = [e for e in wtq.columns if e not in ['f', 'ftem_treatment_id','status']]
            renames = {}
            extra_cols = ['geometry']
            extra_cols = []
            #print(len(wtq))
            wtq = wtq.drop(columns=extra_cols).rename(index=str, columns=renames)
            #wtq = wtq.drop_duplicates('ftem_treatment_id')
            #wtq = gpd.GeoDataFrame(wtq)
            print(wtq.columns)
            #wtq.to_csv(base_dir + 'wt.csv')
            print(len(wtq))
            wtq.crs = {'init': 'epsg:4269'}
            #wtq.to_file(fire_dir + 'test.json', driver="GeoJSON")
            #wtq.crs = {'init': 'epsg:2163'}
            #print(wtq.crs)
            #wtqc = wtq.to_crs(epsg=4326) # EPSG:4326 - WGS 84 - Geographic
            #wtqc = wtq.to_crs(wildfire_gdfc.crs) # EPSG:4326 - WGS 84 - Geographic
            #wtq = pd.DataFrame(wtq)
            extra_cols = ['the_geom']
            wtq = wtq.drop(columns=extra_cols)
            wtq.to_csv(fire_dir + 'test.csv')
            wtt = wtq.groupby(['f', 'ftem_treatment_id', 'definite_interaction', 'status', 'acres_burned', 'wt_agency', 'added_by', 'date_added', 'treatment_name', 'treatment_category', 'treatment_type', 'actual_completion_date', 'treatment_acres', 'treatment_status', 'activity'], as_index=False)
            wtt = wtt.apply(lambda x: x) 
            print(len(wtt))
            wtt.to_csv(fire_dir + 'test.csv')
            #wtqcopy = wtq.copy()
            #print(wtq['status'])
            #quit()
            j = (wtq.groupby(['f', 'ftem_treatment_id', 'definite_interaction', 'status', 'acres_burned', 'wt_agency', 'added_by', 'date_added', 'treatment_name', 'treatment_category', 'treatment_type', 'actual_completion_date', 'treatment_acres', 'treatment_status', 'activity'], as_index=False)
                 .apply(lambda x: x[['header', 'pres_order', 'question', 'response', 'user_id', 'entry_time']].to_dict('r'))
                 .reset_index()
                 .rename(columns={0:'questions'})
                 .reset_index()
                 .to_json(path_or_buf=fire_dir + 'questions.json', orient='records'))

            with open(fire_dir + 'questions.json', 'r') as f:
                array = json.load(f)

            print(wtq)
            print(len(wtq))
            #print(array)
            #quit()

            for item in array:
                ft = pd.DataFrame.from_dict(item['questions']).reset_index(drop=True)
                j = (ft.groupby(['header'], as_index=True)
                     .apply(lambda x: x[['pres_order', 'question', 'response', 'user_id', 'entry_time']].to_dict('r'))
                     .reset_index()
                     .rename(columns={0:'questions'})
                     .reset_index()
                     #.to_json(path_or_buf=fire_dir + 'wtqq.json', orient='records'))
                     .to_json(orient='records'))
                #print(j)
                #quit()
                new_d = dict_sweep(j, 'index') # {'ok': [{'ok': 1}]}
                #print(json.dumps(j, sort_keys=True))
                new_d = json.loads(new_d)
                #print(new_d)
                #print(type(new_d))
                item['questions'] = new_d
                #new_i = dict_sweep(item, 'index')
                #print(type(new_i))

                #with open(fire_dir + 'testitem.json', 'w', encoding='utf-8') as f:
                #    json.dump(new_i, f, ensure_ascii=False, indent=4, default=str)
                #item.reset_index()
                #print(new_i)
                #quit()
            #print(type(item))
            #array.to_json(fire_dir + 'test.json', orient='records')
            new_a = dict_sweep(array, 'index')
            with open(fire_dir + 'questions.json', 'w', encoding='utf-8') as f:
                json.dump(new_a, f, ensure_ascii=False, indent=4, default=str)

            #geojson_topojson(fire_dir + 'questions.json', fire_dir + 'questions.json.packed')

            #geojson_topojson(fire_dir + 'wtqq.json', fire_dir + 'wtqq.json.packed')
            #quit()

            wtq = wildfire_treatments[wildfire_treatments['f'] == wildfire[1]]
            #wtq = wildfire_treatments[wildfire_treatments['f']==83027.0]
            #print(wtq.columns)
            extra_cols = [e for e in wtq.columns if e not in ['f', 'ftem_treatment_id', 'geometry']]
            renames = {}
            #print(len(wtq))
            wtq = wtq.drop(columns=extra_cols).rename(index=str, columns=renames)
            wtq = wtq.drop_duplicates('ftem_treatment_id')
            #print(type(wtq))
            nwa = pd.DataFrame(new_a)
            #print(len(nwa))
            #print(type(nwa))
            #wtq = pd.merge(wtq,nwa, on='ftem_treatment_id')
            #print(wtq)
            #print(new_a)
            #print(nwa.columns)

            #wtq = wtq.update(nwa)
            #print(type(wtq))
            wtq = gpd.GeoDataFrame(wtq)
            #print(wtq.columns)
            #wtq.to_csv(base_dir + 'wt.csv')
            #print(len(wtq))
            wtq.crs = {'init': 'epsg:4269'}
            #wtq.crs = {'init': 'epsg:2163'}
            #print(wtq.crs)
            #wtqc = wtq.to_crs(epsg=4326) # EPSG:4326 - WGS 84 - Geographic
            wtqc = wtq.to_crs(wildfire_gdfc.crs) # EPSG:4326 - WGS 84 - Geographic
            wtqc.to_file(fire_dir + 'wtq.json', driver="GeoJSON")
            geojson_topojson(fire_dir + 'wtq.json', fire_dir + 'wtq.json.packed')
            os.remove(fire_dir + 'wtq.json')
            #quit()
            context = {'f': wildfire[1], 'u': wildfire[3], 'i': wildfire[4], 'geometry': wildfire[2]}
            template = get_template("build_ftem.html")
            content = template.render(context)
            with open(fire_dir + 'index.html', 'w') as static_file:
                static_file.write(content)
            template = get_template("build_ftem.js")
            content = template.render(context)
            with open(fire_dir + 'data.js', 'w') as static_file:
                static_file.write(content)
    quit()

if __name__ == '__main__':
    main()
