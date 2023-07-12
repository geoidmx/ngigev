/**
 * @fileoverview Library to init map visualizations.
 *               Need leafletJs and leaflet-hash libraries.
 * @version 1.0
 * @author Arbekos Gh
 * @copyright geoid.mx
 */

/**
 * DOM Objects
 */

// Modals
const wfsModal = new bootstrap.Modal(document.getElementById("wfs-modal"), {
  keyboard: false,
  backdrop: "static",
});
const shpModal = new bootstrap.Modal(document.getElementById("shp-modal"), {
  keyboard: false,
});
const compareModal = new bootstrap.Modal(
  document.getElementById("compare-modal"),
  {
    keyboard: false,
  }
);

//Buttons
const wfsLoadButton = document.getElementById("wfs-load-button");
const shpLoadButton = document.getElementById("shp-load-button");
const compareButton = document.getElementById("compare-button");

//loading images
const wfsLoading = document.getElementById("wfs-loading");
const shpLoading = document.getElementById("shp-loading");
const compareLoading = document.getElementById("compare-loading");

//download
const downloadBtn = document.getElementById("download-btn");

/**
 * Class representing a Interface to load and update values in DOM objects.
 */
class Interface extends Mapa {
  constructor(mapSettings, wfsSettings, shpSettings, compareSettings) {
    super(mapSettings.mapId, mapSettings.config);
    this.wfs = wfsSettings;
    this.shp = shpSettings;
    this.compare = compareSettings;
  }

  setInterface() {
    this.createMap();
    this.loadServicesWFSData();
  }

  loadServicesWFSData() {
    //get registered WFS services liste
    fetch(this.wfs.servicesUrl, {
      method: "GET",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "X-Requested-Width": "XMLHttpRequest",
      },
    })
      .then((res) => res.json())
      .then((data) => {
        for (let index = 0; index < data.countries.length; index++) {
          let country = data.countries[index].country;
          let serviceHtml = `<h6>${country}</h6>
                                      <ul class="list-group list-group-flush mb-3">`;

          data.services.forEach((element) => {
            if (element.country === country) {
              serviceHtml += `
                                <li class="list-group-item">
                                    <div class="form-check">
                                        <input class="form-check-input" type="radio" name="wfs-services-check" id="flexRadio-${element.id}" 
                                                value="${element.id}" data-country="${element.country}" data-name="${element.name}" data-type="${element.layer_type}">
                                        <label class="form-check-label" for="flexRadio-${element.id}">${element.name}</label>
                                    </div>
                                </li>`;
            }
          });
          serviceHtml += `</ul>`;
          this.wfs.wfsListDOM.innerHTML += serviceHtml;
        }
      })
      .catch((error) => {
        console.log(error);
      });
  }

  loadWFSLayer(layerOpt) {
    //hide button, and show loading image
    wfsLoadButton.style.display = "none";
    wfsLoading.style.display = "block";
    //get map bound visualization
    let bbox = this.map.getBounds();
    //create the query url
    let wfsUrl = `/layers/wfs/load/${layerOpt.id}/${bbox._southWest["lat"]},${bbox._southWest["lng"]},${bbox._northEast["lat"]},${bbox._northEast["lng"]}/`;
    console.log(wfsUrl);
    //sent fetch request
    fetch(wfsUrl, {
      method: "GET",
      mode: "no-cors",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "X-Requested-Width": "XMLHttpRequest",
      },
    })
      .then((response) => {
        //console.log(response.headers.get('Size-Layer'));
        if (!response.ok) {
          throw new Error("No se pudo hacer conexion con el servicio WFS");
        }
        return response.json();
      })
      .then((responseJson) => {
        //add layer to map
        this.addVectorLayer(responseJson, layerOpt);
        //show button, and hide loading image
        wfsLoading.style.display = "none";
        wfsLoadButton.style.display = "block";
        //hide modal
        wfsModal.hide();
      })
      .catch((error) => {
        alert(error);
        //show button, and hide loading image
        wfsLoading.style.display = "none";
        wfsLoadButton.style.display = "block";
        //hide modal
        wfsModal.hide();
      });
  }

  loadSHPLayer(shpFormData, layerOpt) {
    //hide button, and show loading image
    shpLoadButton.style.display = "none";
    shpLoading.style.display = "block";
    //sent fetch request
    fetch(this.shp.loadUrl, {
      method: "POST",
      mode: "no-cors",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "X-Requested-Width": "XMLHttpRequest",
      },
      body: shpFormData,
    })
      .then((response) => {
        return response.json();
      })
      .then((responseJson) => {
        //add vector layer to map
        this.addVectorLayer(responseJson, layerOpt);
        //hide button, and show loading image
        shpLoading.style.display = "none";
        shpLoadButton.style.display = "block";
        //hide modal
        shpModal.hide();
      })
      .catch((error) => {
        alert("ha sucedido un error al cargar tus datos");
        console.log(error);
      });
  }

  updateCompareList(layerOpt) {
    if (layerOpt.type == "point") {
      this.compare.compareListDOM.innerHTML = `
        <ul class="list-group list-group-flush mb-3">
            <li class="list-group-item">
                <h5 class="card-title mb-2">${layerOpt.name} ${layerOpt.country}</h5>
                <h6 class="card-subtitle mb-2 text-muted">${layerOpt.source}</h6>
            </li>
            <li class="list-group-item">
                <div class="form-check">
                    <input class="form-check-input" type="radio" name="compareRadios" id="compareRadios1" 
                    data-source="${layerOpt.source}" data-layer="${layerOpt.id}" data-type="${layerOpt.type}" 
                    data-name="Diferencias ${layerOpt.name} Fuentes de datos" value="oficial" checked>
                    <label class="form-check-label" for="compareRadios1">
                      Diferencias entre Fuentes de Datos 
                    </label>
                </div>
            </li>
        </ul>`;
    } else {
      this.compare.compareListDOM.innerHTML = `
        <ul class="list-group list-group-flush mb-3">
            <li class="list-group-item">
                <h5 class="card-title mb-2">${layerOpt.name} ${layerOpt.country}</h5>
                <h6 class="card-subtitle mb-2 text-muted">${layerOpt.source}</h6>
            </li>
            <li class="list-group-item">
                <div class="form-check">
                    <input class="form-check-input" type="radio" name="compareRadios" id="compareRadios1" 
                    data-source="${layerOpt.source}" data-layer="${layerOpt.id}" data-type="${layerOpt.type}" 
                    data-name="Diferencia ${layerOpt.name} de Fuente Oficial vs OSM" value="oficial" checked>
                    <label class="form-check-label" for="compareRadios1">
                      Diferencias entre Fuente Oficial - OSM
                    </label>
                </div>
                <div class="form-check">
                  <input class="form-check-input" type="radio" name="compareRadios" id="compareRadios2" 
                  data-source="${layerOpt.source}" data-layer="${layerOpt.id}" data-type="${layerOpt.type}" 
                  data-name="Diferencia ${layerOpt.name} de OSM vs Fuente Oficial" value="osm">
                  <label class="form-check-label" for="exampleRadios2">
                    Diferencias entre OSM - Fuente Oficial
                  </label>
                </div>
            </li>
        </ul>`;
    }
    compareButton.classList.remove("disabled");
  }

  compareDataSources(compareOpt) {
    //hide button, and show loading image
    compareButton.style.display = "none";
    compareLoading.style.display = "block";

    //get map bound visualization
    let bbox = this.map.getBounds();
    let compareUrl = `/map/compare/${compareOpt.source}/${compareOpt.layer}/${compareOpt.value}/${bbox._southWest["lat"]},${bbox._southWest["lng"]},${bbox._northEast["lat"]},${bbox._northEast["lng"]}/`;
    console.log(compareUrl);
    fetch(compareUrl, {
      method: "GET",
      mode: "no-cors",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "X-Requested-Width": "XMLHttpRequest",
      },
    })
      .then((response) => {
        return response.json();
      })
      .then((responseJson) => {
        //add vector layer to map
        this.addVectorLayer(responseJson, compareOpt);
        //save in local storage
        localStorage.setItem(compareOpt.name, JSON.stringify(responseJson));
        downloadBtn.setAttribute("data-name", compareOpt.name);
        downloadBtn.classList.remove("disabled");
        //hide button, and show loading image
        compareLoading.style.display = "none";
        compareButton.style.display = "block";
        //hide modal
        compareModal.hide();
      })
      .catch((error) => {
        alert("No se encontraron datos para comparar");
        console.log(error);
        compareButton.textContent = "Comparar";
        //hide modal
        compareModal.hide();
      });
  }

  loadOSMPoints(compareOpt) {
    let options = {
      name: "Puntos OSM",
      action: "loadPoints",
      type: "point",
    };
    //get map bound visualization
    let bbox = this.map.getBounds();
    //create the query url
    let pointsUrl = `/layers/osm/load/${compareOpt.source}/${compareOpt.layer}/${bbox._southWest["lat"]},${bbox._southWest["lng"]},${bbox._northEast["lat"]},${bbox._northEast["lng"]}/`;
    console.log(pointsUrl);
    fetch(pointsUrl, {
      method: "GET",
      mode: "no-cors",
      credentials: "same-origin",
      headers: {
        Accept: "application/json",
        "X-Requested-Width": "XMLHttpRequest",
      },
    })
      .then((response) => {
        return response.json();
      })
      .then((responseJson) => {
        //add vector layer to map
        this.addVectorLayer(responseJson, options);
      })
      .catch((error) => {
        alert("No se encontraron datos para comparar");
        console.log(error);
      });
  }
}
