var l = document.getElementById('left');
l.innerHTML += 'Wildfire Perimeter with Nearby Fuel Treatments';

var r = document.getElementById('right');
r.innerHTML += '{{i}} &sect {{u}}';

var map = L.map('map', {
    zoom: 7,
    preferCanvas: true,
    maxBounds: [[-90, -200], [90, 180]],
    maxZoom: 17,
    minZoom: 2,
    fullscreenControl: true,
    fullscreenControlOptions: {
       position: 'bottomleft'
    },
    attributionControl: false,
    attributionControlOptions: {
       prefix: ''
    },
    zoomControl: true,
});

    var cFull = L.control({
        position: 'bottomleft'
    });
    cFull.onAdd = function(map) {
        var div = L.DomUtil.create('div', 'leaflet-control-zoom leaflet-bar leaflet-control');
        div.id += 'full-extent-btn';
        div.innerHTML += '<a class="leaflet-control-zoom-home home-icon" href="#" title="Full extent" role="button" aria-label="Full extent"><span class=\'glyphicon glyphicon-bookmark small\'></span></a>';
        return div;
    };
    cFull.addTo(map);

    $("#full-extent-btn").click(function() {
      map.fitBounds(L.featureGroup([omniLayer, omniLayer2]).getBounds());  
      return false;
    });

    var info = L.control({
        position: 'topleft'
    });
    info.onAdd = function(map) {
        var div = L.DomUtil.create('div', 'info');
        div.id += 'perims';
        div.style = 'background-color:"White";border:1px;'
        div.innerHTML += '<small></small>';
        return div;
    };
    info.addTo(map);

var bl = L.geoJSON(null, {
  style: {
    color: 'Black',
    fillColor:  'HotPink',
    fillOpacity: 0.1,
    weight: 1.5,
    opacity: 1
    },
  smoothFactor: 0.5
}).addTo(map);

var fb = omnivore.topojson('datb.json.packed', null, bl);

var fireIcon = L.divIcon({className: 'fireIcon'});

var fireLayer = L.geoJSON(null, {
  style: {
    color: 'Black',
    fillColor:  'HotPink',
    fillOpacity: 0.2,
    weight: 1.5,
    opacity: 1
    },
  smoothFactor: 0.5,
      pointToLayer: function (feature, latlng) {
        return L.marker(latlng, {icon: fireIcon});
    }
}).addTo(map);

var omniLayer2 = omnivore.topojson('data.json.packed', null, fireLayer);

var tIcon = L.divIcon({className: 'tIcon'});

var tLayer = L.geoJson(null, {
  style: {
      color: 'Black',
      fillColor:  'Black',
      fillOpacity: 0,
      dashArray: '2,4',
      weight: 2,
      opacity: 1//,
    },
  smoothFactor: 0.5,
      pointToLayer: function (feature, latlng) {
        return L.marker(latlng, {icon: tIcon});
    }
}).addTo(map);

var omniLayer = omnivore.topojson('wtq.json.packed', null, tLayer);

var highlighted = {
    'color': 'Black',
    'fillOpacity': 0.9,
    'weight': 3
};

omniLayer.on('ready', function() {
  $.getJSON('questions.json').done(addTopoData);
  map.fitBounds(omniLayer2.getBounds());
  omniLayer.bringToFront();
});

function addTopoData(results) {
      tLayer.eachLayer(function(layer) {
        featureJoinByProperty(layer.feature.properties, results, "ftem_treatment_id");
      });
      tLayer.eachLayer(function(layer) {
        layer.setStyle(tStyle(layer));
        layer.on({
          click: function (e) {
              content = 'name: <strong>' + layer.feature.properties.treatment_name + '</strong><br>type: <strong>' + layer.feature.properties.treatment_type + '</strong><br>category: <strong>' + layer.feature.properties.treatment_category + '</strong><br>activity: <strong>' + layer.feature.properties.activity + '</strong><br>acres: <strong>' + layer.feature.properties.treatment_acres + '</strong><br>status: <strong>' + layer.feature.properties.status 
              bold('perims', content);
              tLayer.eachLayer(function(layer) {
                layer.setStyle(tStyle(layer));
              });
              layer.setStyle(highlighted);
              map.fitBounds(layer.getBounds());
          },
        });
      }); 
    }

var baseLayers = getCommonBaseLayers(map);

var olsr = {
    "<i class='glyphicon glyphicon-stop' style='color:cyan'></i> completed<br><i class='glyphicon glyphicon-stop' style='color:white;margin-right:5px'></i> <i class='glyphicon glyphicon-stop' style='color:orange'></i> in progress<br><i class='glyphicon glyphicon-stop' style='color:white;margin-right:5px'></i> <i class='glyphicon glyphicon-stop' style='color:red'></i> not started<br>": tLayer,
    "<i class='glyphicon glyphicon-circle' style='color:hotpink;opacity:1'></i> wildfire point<br><i class='glyphicon glyphicon-stop' style='color:white;margin-right:5px'></i> <i class='glyphicon glyphicon-stop' style='color:hotpink;opacity:0.2'></i> wildfire polygon": fireLayer,
    "<i class='glyphicon glyphicon-stop' style='color:hotpink;opacity:0.1'></i> wildfire buffer": bl
};

rc = L.control.layers({}, olsr, {collapsed:false}).addTo(map);

L.control.layers(baseLayers, {}).addTo(map);

function bold(targetC, content) {
    var theDiv = document.getElementById(targetC);
    theDiv.innerHTML = content;
}

function featureJoinByProperty(fProps, dTable, joinKey) {
  var keyVal = fProps[joinKey];
  var match = {};
  for (var i = 0; i < dTable.length; i++) {
    if (dTable[i][joinKey] === keyVal) {
      match = dTable[i];
      for (key in match) {
        if (!(key in fProps)) {
          fProps[key] = match[key];
        }
      }
    }
  }
}

function tStyle (layer) {
    return {
        fillColor: getColor(layer.feature.properties.status),
        dashArray: '2,4',
        weight: 2,
        opacity: 0.8,
        fillOpacity: getOpacity(layer.feature.properties.status)
    };
}

function getColor(y) {
    return y == 'comp' ? 'Cyan' :
           y == 'inpr' ? 'Orange' :
           y == 'nots' ? 'Red' :
                      'Black';
}

function getOpacity(y) {
    return y == 'comp' ? 0.8 :
           y == 'inpr' ? 0.8 :
           y == 'nots' ? 0.8 :
                      0;
}

$("#about-btn").click(function() {
  $("#aboutModal").modal("show");
  $(".navbar-collapse.in").collapse("hide");
  return false;
});

$("#info-btn").click(function() {
  $("#infoModal").modal("show");
  $(".navbar-collapse.in").collapse("hide");
  return false;
});
