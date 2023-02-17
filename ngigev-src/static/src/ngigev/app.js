/**
 * DOM Objects
 */
// WFS Objects
const wfsForm = document.getElementById("wfs-form");
const wfsRadios = document.getElementsByName("wfs-services-check");
const wfsList = document.getElementById("wfs-list");

// SHP Objects
const shpForm = document.getElementById("shp-form");
const shpNameInput = document.getElementById("id_name");
const shpTypeInput = document.getElementById("id_layer_type");

// Comparision Objects
const compareForm = document.getElementById("compare-form");
const compareList = document.getElementById("compare-list");
const compareRadios = document.getElementsByName("compareRadios");

// Initial Settings
const mapSettings = {
  mapId: "map",
  config: {
    initCoords: [13.336829, -90.043945],
    zoom: 5,
  },
};

const wfsSettings = {
  servicesUrl: "/layers/services-wfs/",
  wfsListDOM: wfsList,
};

const shpSettings = {
  loadUrl: "/layers/shp/load/",
};

const compareSettings = {
  compareListDOM: compareList,
};

ngigevInterfaz = new Interface(
  mapSettings,
  wfsSettings,
  shpSettings,
  compareSettings
);

ngigevInterfaz.setInterface();

/***
 * Listeners
 * **/
wfsForm.addEventListener("submit", function (e) {
  e.preventDefault();
  //get values selected from wfs modal
  let wfsSelected;
  for (var i = 0, n = wfsRadios.length; i < n; i++) {
    if (wfsRadios[i].checked) {
      wfsSelected = {
        id: wfsRadios[i].value,
        country: wfsRadios[i].getAttribute("data-country"),
        name: wfsRadios[i].getAttribute("data-name"),
        type: wfsRadios[i].getAttribute("data-type"),
        action: "load",
        source: "WFS",
      };
      break;
    }
  }
  //load layer in the map
  ngigevInterfaz.loadWFSLayer(wfsSelected);
  //update values to make comparision in compare modal
  ngigevInterfaz.updateCompareList(wfsSelected);
});

shpForm.addEventListener("submit", function (e) {
  e.preventDefault();
  //create the formdata
  const formData = new FormData(shpForm);

  let shpSelected = {
    id: shpNameInput.value,
    country: "",
    name: shpNameInput.value,
    type: shpTypeInput.value,
    action: "load",
    source: "SHP",
  };
  //load shp layers
  ngigevInterfaz.loadSHPLayer(formData, shpSelected);
  //update values to make comparision in compare modal
  ngigevInterfaz.updateCompareList(shpSelected);
});

compareForm.addEventListener("submit", function (e) {
  e.preventDefault();
  //get values selected from compare modal
  let comparisonSelected;
  for (var i = 0, n = compareRadios.length; i < n; i++) {
    if (compareRadios[i].checked) {
      comparisonSelected = {
        value: compareRadios[i].value,
        layer: compareRadios[i].getAttribute("data-layer"),
        source: compareRadios[i].getAttribute("data-source"),
        name: compareRadios[i].getAttribute("data-name"),
        type: compareRadios[i].getAttribute("data-type"),
        action: "compare",
      };
      break;
    }
  }
  
  //if compare points, load osm layer
  if (comparisonSelected.type === "point") {
    ngigevInterfaz.loadOSMPoints(comparisonSelected);
  }
  //compare data sources
  ngigevInterfaz.compareDataSources(comparisonSelected);
});

downloadBtn.addEventListener("click", function (e) {
  e.preventDefault();
  // get data
  data = localStorage.getItem(this.getAttribute("data-name"));
  // create link
  let tempLink = document.createElement("a");
  let dataBlob = new Blob([data], { type: "text/plain" });
  tempLink.setAttribute("href", URL.createObjectURL(dataBlob));
  tempLink.setAttribute("download", `${this.getAttribute("data-name")}.json`);
  tempLink.click();
  URL.revokeObjectURL(tempLink.href);
});
