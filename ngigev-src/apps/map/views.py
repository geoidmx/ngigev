# -*- encoding: utf-8 -*-
from django.shortcuts import render, redirect
from django.views.generic import View
from django.views.generic.base import TemplateView
from django.http import HttpResponse

from owslib.wfs import WebFeatureService
from requests import Request
import json
import os

from apps.layers.forms import TemporaryShpForm
from apps.layers.models import TemporaryShp
from .comparisions import CompareWithWFS, CompareWithSHP


class MapView(TemplateView):
    template_name = "map.html"

    def get_context_data(self, **kwargs):
        context = super(MapView, self).get_context_data(**kwargs)
        form = TemporaryShpForm  # instance= None
        context["form"] = form
        return context


class CompareDataView(View):

    def get(self, request, *args, **kwargs):
        # get values to compare
        data_source = self.kwargs['source']
        comparision_option = self.kwargs['option']

        # compare by data source
        if data_source == 'WFS':
            layer_id = self.kwargs['pk']
            bbox = self.kwargs['bbox']
            compare_with_wfs = CompareWithWFS(
                layer_id, comparision_option, bbox)
            # get comparision
            comparision = compare_with_wfs.compare()
            # clean temp files
            self.clean_wfs_comparision()
            # return comparision
            return comparision
        elif data_source == 'SHP':
            layer_name = self.kwargs['name']
            compare_with_shp = CompareWithSHP(layer_name, comparision_option)
            # get comparision
            comparision = compare_with_shp.compare()
            # clean temp files
            self.clean_shp_comparision()
            # return comparision
            return comparision
        else:
            # return empty
            wfs_data = {}
            return HttpResponse(json.dumps(wfs_data), content_type='application/json')

    def clean_shp_comparision(self):
        # delete temporary object
        layer_name = self.kwargs['name']
        if TemporaryShp.objects.filter(name=layer_name).exists():
            # get object
            layer = TemporaryShp.objects.filter(name=layer_name)[0]
            # get shp file name
            shp_file = layer.shp_file_path.split('.')[0]
            # clean temporary shp directory
            temp_dir = "media/temp"
            for file in os.listdir(temp_dir):
                if file.split('.')[0] == shp_file:
                    os.remove(os.path.join(temp_dir, file))
            # delete object
            layer.delete()
            # clean cache directory
            temp_dir = "cache"
            for file in os.listdir(temp_dir):
                os.remove(os.path.join(temp_dir, file))

    def clean_wfs_comparision(self):
        # clean cache directory
        temp_dir = "cache"
        for file in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, file))
