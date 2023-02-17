/**
 * @fileoverview Library to init map visualizations.
 *               Need leafletJs and leaflet-hash libraries.
 * @version 1.0
 * @author Arbekos Gh
 * @copyright geoid.mx
 */

/**
 * Class representing a map.
 */
class Mapa {
  /**
   * Create the map on the DOM Object with the id
   * @param {string} mapId the DOM Object Id for the map
   * @param {json} mapConfig the flashmap user configuration
   * @var {object} map leaflet map
   * @var {array} activeLayers manages the layers displayed on map
   */
  constructor(mapId, mapConfig) {
    this.mapId = mapId;
    this.mapSettings = mapConfig;
    //init objects
    this.map;
    this.layerControl;
  }

  /**
   * Initialize the functions to implement the map display
   */
  createMap() {
    this.setMap();
    this.addBaseMaps();
    this.addBaseControls();
  }

  /**
   * Set the leaflet map on the DOM Object
   */
  setMap() {
    this.map = L.map(this.mapId, {}).setView(
      this.mapSettings.initCoords,
      this.mapSettings.zoom
    );
    this.activeLayers = L.layerGroup().addTo(this.map);
    let hash = new L.Hash(this.map);
  }

  /**
   * Add the basemap tilelayer defined in the map settings
   */
  addBaseMaps() {
    // token and attribution mapbox
    const token =
      "pk.eyJ1IjoibWFwYm94IiwiYSI6ImNpejY4NXVycTA2emYycXBndHRqcmZ3N3gifQ.rJcFIG214AriISLbB6B5aw";
    const mbAttr = `Map data &copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> 
                      contributors, Imagery © <a href="https://www.mapbox.com/">Mapbox</a>`,
      mbUrl = `https://api.mapbox.com/styles/v1/{id}/tiles/{z}/{x}/{y}?access_token={accessToken}`;
    // tile basemaps
    const satellite = L.tileLayer(mbUrl, {
        attribution: mbAttr,
        tileSize: 512,
        zoomOffset: -1,
        id: "mapbox/satellite-v9",
        accessToken: token,
      }),
      streets = L.tileLayer(mbUrl, {
        attribution: mbAttr,
        tileSize: 512,
        zoomOffset: -1,
        id: "mapbox/streets-v11",
        accessToken: token,
      }),
      osm = L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
        maxZoom: 19,
        attribution:
          '&copy; <a href="http://www.openstreetmap.org/copyright">OpenStreetMap</a>',
      });

    //add the initial basemap
    osm.addTo(this.map);

    //create basemap layers list
    let baseLayers = {
      OpenStreetMap: osm,
      MapboxStreets: streets,
      MapboxSatellite: satellite,
    };
    //add basemap tilelayer control
    this.layerControl = L.control
      .layers(baseLayers, null, { position: "topright" })
      .addTo(this.map);
  }

  /**
   * Add controls on the initial map
   */
  addBaseControls() {
    //set the controls positions
    this.map.zoomControl.setPosition("bottomright");
    this.map.addControl(new L.Control.Fullscreen().setPosition("bottomright"));
  }

  /**
   * Add vector layer on the map
   */
  addVectorLayer(geojson, layerOpt) {
    //set layer name
    const layerName =
      layerOpt.action == "show"
        ? `${layerOpt.name} ${layerOpt.country}`
        : layerOpt.name;

    //create vectorgrid
    let vectorGridGeojson = L.vectorGrid.slicer(
      geojson,
      this.optionsVector(layerOpt)
    );

    //set popup
    vectorGridGeojson.on("mouseover", (e) => {
      this.map.eachLayer((layer) => {
        var properties = e.layer.properties;
        if (layer.name == layerName) {
          L.popup()
            .setContent(
              layerOpt.action == "compare" && layerOpt.type == "point"
                ? `puntos:<strong>${properties.total_points}</strong><br/>valor:<strong>${properties.value}</strong>`
                : properties.value
            )
            .setLatLng(e.latlng)
            .openOn(this.map);
        }
      });
    });

    //set name
    vectorGridGeojson.name = layerName;
    vectorGridGeojson.addTo(this.map);
    //add layer to layer control
    this.layerControl.addOverlay(vectorGridGeojson, layerName);
    //add legend
    this.addLegend(layerOpt, vectorGridGeojson);
  }

  optionsVector(layerOpt) {
    return {
      rendererFactory: L.canvas.tile,
      vectorTileLayerStyles: {
        sliced: function (properties, zoom) {
          if (layerOpt.action == "compare" && layerOpt.type == "point") {
            let p = properties.value;
            return {
              fillColor:
                p === "sin_nom"
                  ? "#b9d7d9"
                  : p === "nom_osm"
                  ? "#d14334"
                  : p === "nom_wfs"
                  ? "#028f76"
                  : p === "hay_nom"
                  ? "#ffeaad"
                  : "#FFEDA0",
              fillOpacity: 0.8,
              stroke: true,
              fill: true,
              color: "#003366",
              opacity: 0.7,
              weight: 3,
            };
          } else {
            return {
              fillColor: layerOpt.action == "load" ? "#003366" : "#CAA45D",
              fillOpacity: 0.8,
              stroke: true,
              fill: true,
              color: layerOpt.action == "load" ? "#003366" : "#CAA45D",
              opacity: 0.7,
              weight: 3,
              radius: 10,
            };
          }
        },
      },
      maxZoom: 18,
      tolerance: 5, // simplification tolerance (higher means simpler)
      extent: 4096, // tile extent (both width and height)
      buffer: 64, // tile buffer on each side
      debug: 0, // logging level (0 to disable, 1 or 2)
      zIndex: 15, // max zoom in the initial tile index
      indexMaxPoints: 100000, // max number of points per tile in the index
      interactive: true,
      getFeatureId: function (f) {
        return f.properties.num;
      },
    };
  }

  addLegend(layerOpt, layer) {
    //make legends
    let legends = [];
    switch (layerOpt.type) {
      case "point":
        if (layerOpt.action != "compare") {
          legends = [
            {
              label: layer.name,
              type: "circle",
              radius: 8,
              color: layerOpt.action == "load" ? "#003366" : "#CAA45D",
              fillColor: layerOpt.action == "load" ? "#003366" : "#CAA45D",
              fillOpacity: 0.7,
              weight: 3,
              layers: [layer],
            },
          ];
        } else if (layerOpt.action == "compare") {
          legends = [
            {
              label: "Sin Nombres",
              type: "polygon",
              sides: 6,
              color: "#003366",
              fillColor: "#b9d7d9",
              weight: 1,
              layers: [layer],
            },
            {
              label: "Nombres OSM",
              type: "polygon",
              sides: 6,
              color: "#003366",
              fillColor: "#d14334",
              weight: 1,
              layers: [layer],
            },
            {
              label: "Nombres Oficiales",
              type: "polygon",
              sides: 6,
              color: "#003366",
              fillColor: "#028f76",
              weight: 1,
              layers: [layer],
            },
            {
              label: "Nombres Coincidentes",
              type: "polygon",
              sides: 6,
              color: "#003366",
              fillColor: "#ffeaad",
              weight: 1,
              layers: [layer],
            },
          ];
        }
        break;
      case "line":
        legends = [
          {
            label: layer.name,
            type: "polyline",
            color: layerOpt.action == "load" ? "#003366" : "#CAA45D",
            fillColor: layerOpt.action == "load" ? "#003366" : "#CAA45D",
            fillOpacity: 0.7,
            weight: 3,
            layers: [layer],
          },
        ];
        break;
      default:
        break;
    }
    //add control
    const legend = L.control
      .Legend({
        position: "bottomleft",
        legends: legends,
      })
      .addTo(this.map);
  }
}

//const map = new Map("map", {
//  initCoords: [13.336829, -90.043945],
//  zoom: 5,
//});
//map.createMap();
