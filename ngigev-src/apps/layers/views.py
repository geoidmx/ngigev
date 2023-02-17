# -*- encoding: utf-8 -*-
from django.shortcuts import render, redirect
from django.views.generic import View
from django.views.generic.edit import FormView
from django.http import HttpResponse, JsonResponse
from django.db.models import Count

from owslib.wfs import WebFeatureService
from requests import Request

import json
import pandas as pd
import geopandas as gpd
import osmnx as ox
import numpy as np
import os
import sys

from .models import WFSService, TemporaryShp
from .forms import TemporaryShpForm


class WFSServicesView(View):
    """
        WFS Services list all the services resgistered in the webapp,
        manages the wfs model
    """
    model = WFSService

    def get(self, request, *args, **kwargs):
        # get registered WFS services
        services = self.model.objects.values(
            'id', 'name', 'country', 'layer_type')
        countries = self.model.objects.values(
            'country').annotate(services=Count('country'))
        # create dictionary
        wfs_services = {
            'countries': list(countries),
            'services': list(services)
        }
        # create json
        jdata = json.dumps(wfs_services)
        return HttpResponse(jdata, content_type='application/json')


class LoadTemporaryShpView(FormView):
    form_class = TemporaryShpForm
    model = TemporaryShp

    def post(self, request, *args, **kwargs):
        # delete objects
        self.clean_model()
        # get form
        form_class = self.get_form_class()
        form = self.get_form(form_class)
        # get shp files
        files = request.FILES.getlist('shp_field')
        if form.is_valid():
            for f in files:
                # uplod flie
                self.handle_upload_file(f)
                # get extension file
                extension_file = f.name.split(".")[-1]
                if extension_file == "shp":
                    shp_file = f.name
            # save temporary shp
            temporary_shp = self.form_valid(form, shp_file)
            # return shp in json
            return self.showTemporaryShp(temporary_shp)
        else:
            return HttpResponse('{}', content_type='application/json')

    def form_valid(self, form, shp_file):
        temporaryShp = form.save(commit=False)
        # set shp file name
        temporaryShp.shp_file_path = shp_file
        temporaryShp.save()
        return temporaryShp

    def handle_upload_file(self, f):
        # upload un temporal directory
        # TODO check extensions to uploads
        with open('media/temp/' + f.name, 'wb+') as destination:
            for chunk in f.chunks():
                destination.write(chunk)

    def showTemporaryShp(self, temporaryShp):
        shp_file = gpd.read_file(r"media/temp/" + temporaryShp.shp_file_path)
        # Reproject shp file
        shp_file = shp_file.set_crs(temporaryShp.layer_crs)
        shp_file = shp_file.to_crs('epsg:4326')
        # rename variable
        shp_file.rename(
            columns={temporaryShp.variable_shp: 'value'}, inplace=True)
        jLayer = shp_file.to_json()
        return HttpResponse(jLayer, content_type='application/json')

    def clean_model(self):
        # remove all registers in model
        self.model.objects.all().delete()
        # clean temporary directory
        shp_dir = "media/temp"
        for file in os.listdir(shp_dir):
            os.remove(os.path.join(shp_dir, file))


class LoadWFSView(View):
    """
        Get data from wfs service by bbox, and reproject from the map in json
    """
    model = WFSService

    def get(self, request, *args, **kwargs):
        # delete objects
        # self.clean_model()
        # get wfs serivice id, and bbox to view data
        wfs_id = self.kwargs['pk']
        wfs_bbox = self.kwargs['bbox']

        # get register
        wfs_registered = self.model.objects.get(pk=wfs_id)
        # reproject coords bbox to wfs crs
        bbox_coords = self.get_bbox_coords(wfs_bbox, wfs_registered.layer_crs)
        # Set web feature service
        wfs = WebFeatureService(url=wfs_registered.url)
        # Specify the parameters for fetching the data
        params = dict(service='WFS',
                      version="1.0.0", request='GetFeature',
                      typeName=wfs_registered.layer,
                      bbox=bbox_coords)

        # Generate request
        q = Request('GET', wfs_registered.url, params=params).prepare().url
        # read request
        try:
            # Read data from URL
            wfs_layer = gpd.read_file(q)
        except:
            return JsonResponse({}, status=500)

        # set and reproject layer in wgs-84 / epsg 4386; map crs
        wfs_layer = wfs_layer.set_crs(wfs_registered.layer_crs)
        wfs_layer = wfs_layer.to_crs('epsg:4326')
        # simplify layer
        if wfs_registered.tag_wfs != 'ninguno':
            wfs_layer = wfs_layer.query(wfs_registered.tag_wfs)
        wfs_layer = wfs_layer[[wfs_registered.variable_wfs, "geometry"]]
        # rename variable
        wfs_layer.rename(
            columns={wfs_registered.variable_wfs: 'value'}, inplace=True)
        # create identifier 
        wfs_layer["num"] = np.arange(len(wfs_layer))
        
        # Return json
        jLayer = wfs_layer.to_json()
        # get size layer
        size_layer = round((sys.getsizeof(jLayer)/1048576), 2)
        return HttpResponse(jLayer, content_type='application/json', headers={"Size-Layer": size_layer})

    def get_bbox_coords(self, wfs_bbox, source_epsg):
        # create dataframe and geodataframe
        south, west, north, east = wfs_bbox.split(',')
        bbox_df = pd.DataFrame(
            {'longitude': [west, east], 'latitude': [south, north]})
        bbox_gdf = gpd.GeoDataFrame(geometry=gpd.points_from_xy(
            bbox_df.longitude, bbox_df.latitude))
        # set and reproject crs
        bbox_gdf = bbox_gdf.set_crs('epsg:4326')
        bbox_gdf = bbox_gdf.to_crs(source_epsg)
        # convert to json
        bbox_json = json.loads(bbox_gdf.to_json())
        south, west = bbox_json['features'][0]['geometry']['coordinates']
        north, east = bbox_json['features'][1]['geometry']['coordinates']
        # return in string coords
        return str(south) + ',' + str(west) + ',' + str(north) + ',' + str(east)

    def clean_model(self):
        # clean temporary directory
        shp_dir = "media/temp"
        for file in os.listdir(shp_dir):
            os.remove(os.path.join(shp_dir, file))


class LoadOSMPoints(View):
    """
        Get points from osm service by bbox or boundary
    """
    wfs_model = WFSService
    shp_model = TemporaryShp

    def get(self, request, *args, **kwargs):
        # get data source
        data_source = self.kwargs['source']

        # load points by data source
        if data_source == 'WFS':
            # get id and bbox
            layer_id = self.kwargs['pk']
            bbox = self.kwargs['bbox']
            # get wfs layer
            layer = self.wfs_model.objects.get(id=layer_id)
            # return osm points
            return self.load_points_by_bbox(layer, bbox)
        elif data_source == 'SHP':
            # get layer
            layer_name = self.kwargs['name']
            # get shp layer
            layer = self.shp_model.objects.get(name=layer_name)
            return self.load_points_by_place(layer)
        else:
            data = {}
            return HttpResponse(json.dumps(data), content_type='application/json')

    def load_points_by_bbox(self, wfs, bbox):
        # bbox
        south, west, north, east = bbox.split(',')
        # Download OSM data
        # network_type define un registes source wfs
        tags = {wfs.tag_osm: True}
        osm_objects = ox.geometries_from_bbox(
            float(north), float(south), float(east), float(west), tags)
        # get only points
        osm_objects = osm_objects[osm_objects.geom_type == 'Point']
        # simplify two vars
        osm_objects = osm_objects[[wfs.variable_osm, "geometry"]]
        # Rename field variable to be able to identify it when merging into a single H3 table
        osm_objects.rename(columns={wfs.variable_osm: 'value'}, inplace=True)
        # create index
        osm_objects["num"] = np.arange(len(osm_objects))
        osm_objects = osm_objects.set_index("num")
        # return osm_objects
        return HttpResponse(osm_objects.to_json(), content_type='application/json')

    def load_points_by_place(self, shp):
        # Download OSM data
        # geocode
        # TODO tag_osm
        tags = {'place': True}
        osm_objects = ox.geometries_from_place(shp.boundary, tags)
        # get only points
        osm_objects = osm_objects[osm_objects.geom_type == 'Point']
        # simplify two vars
        variable = shp.variable_osm.lower()
        osm_objects = osm_objects[[variable, "geometry"]]
        # Rename field variable to be able to identify it when merging into a single H3 table
        osm_objects.rename(columns={variable: 'value'}, inplace=True)
        # create index
        osm_objects["num"] = np.arange(len(osm_objects))
        osm_objects = osm_objects.set_index("num")
        # return osm_objects
        return HttpResponse(osm_objects.to_json(), content_type='application/json')
