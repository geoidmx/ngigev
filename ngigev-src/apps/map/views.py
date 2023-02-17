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
from apps.layers.models import WFSService
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
            # clean temp files
            self.clean_model()
            layer_id = self.kwargs['pk']
            bbox = self.kwargs['bbox']
            compare_with_wfs = CompareWithWFS(
                layer_id, comparision_option, bbox)
            # return comparision
            return compare_with_wfs.compare()
        elif data_source == 'SHP':
            layer_name = self.kwargs['name']
            compare_with_shp = CompareWithSHP(layer_name, comparision_option)
            # return comparision
            return compare_with_shp.compare()
        else:
            # return empty
            wfs_data = {}
            return HttpResponse(json.dumps(wfs_data), content_type='application/json')

    def clean_model(self):
        # clean temporary directory
        temp_dir = "media/temp"
        for file in os.listdir(temp_dir):
            os.remove(os.path.join(temp_dir, file))
