from apps.layers.models import WFSService, TemporaryShp
from django.http import HttpResponse
from owslib.wfs import WebFeatureService
from requests import Request
import json
import pandas as pd
import geopandas as gpd
import osmnx as ox
import numpy as np
import h3
from shapely.geometry import Polygon
import fiona
import difflib as dfl


class CompareWithWFS:

    def __init__(self, layer_id, comparision_option, bbox):
        self.comparision_option = comparision_option
        self.bbox = bbox
        self.h3_level = 7
        self.wfs = WFSService.objects.get(pk=layer_id)

    def compare(self):
        # process by layer type
        if self.wfs.layer_type == 'line':
            # get objects
            oficial_objects = self.get_wfs_line_objects()
            osm_objects = self.get_osm_line_objects()
            # return comparision
            return self.compare_linear_objects(oficial_objects, osm_objects)
        elif self.wfs.layer_type == 'point':
            # get objects
            oficial_objects = self.get_wfs_point_objects()
            osm_objects = self.get_osm_point_objects()
            # return comparision
            return self.compare_point_objects(oficial_objects, osm_objects)
        else:
            return HttpResponse(json.dumps({}), content_type='application/json')

    def get_wfs_line_objects(self):
        # reproject coords bbox to wfs crs
        bbox_coords = self.get_wfs_bbox_coords()
        # Set web feature service
        wfs = WebFeatureService(url=self.wfs.url)
        # Specify the parameters for fetching the data
        params = dict(service='WFS',
                      version="1.0.0", request='GetFeature',
                      typeName=self.wfs.layer,
                      bbox=bbox_coords)
        # Generate request
        q = Request('GET', self.wfs.url, params=params).prepare().url
        # Read data from URL
        wfs_layer = gpd.read_file(q)
        # set src
        wfs_layer = wfs_layer.set_crs(self.wfs.layer_crs)
        # simplify two vars
        wfs_layer = wfs_layer[[self.wfs.variable_wfs, "geometry"]]
        return wfs_layer

    def get_osm_line_objects(self):
        # bbox
        south, west, north, east = self.bbox.split(',')
        # Download OSM data
        # network_type define un registes source wfs
        osm_objects = ox.graph_from_bbox(float(north), float(south), float(
            east), float(west), network_type=self.wfs.tag_osm)
        osm_nodes, osm_edges = ox.graph_to_gdfs(osm_objects)
        # simplify two vars
        osm_edges = osm_edges[[self.wfs.variable_osm, "geometry"]]
        # create index
        osm_edges["num"] = np.arange(len(osm_edges))
        osm_edges = osm_edges.set_index("num")
        # return only edges
        return osm_edges

    def compare_linear_objects(self, oficial_objects, osm_objects):
        # set reprojection
        oficial_objects = oficial_objects.to_crs(self.wfs.layer_crs)
        osm_objects = osm_objects.to_crs(self.wfs.layer_crs)
        # create buffer
        oficial_objects["buffered"] = oficial_objects.buffer(10)
        osm_objects["buffered"] = osm_objects.buffer(10)
        # compare data
        if self.comparision_option == 'oficial':
            return self.compare_oficial_linear_objects(oficial_objects, osm_objects)
        elif self.comparision_option == 'osm':
            return self.compare_osm_linear_objects(oficial_objects, osm_objects)

    def compare_oficial_linear_objects(self, oficial_objects, osm_objects):
        # set buffer in variables
        osm_buffer = osm_objects.set_geometry("buffered")
        wfs_buffer = oficial_objects.set_geometry("buffered")
        # Result A: exist in WFS and not in OSM
        # difference overlap by buffer
        overlap_difference = gpd.overlay(
            wfs_buffer, osm_buffer, how='difference')
        oficial_lines = oficial_objects.set_geometry("geometry")
        overlap_buffer = overlap_difference.set_geometry("buffered")
        # interesenction buffer with oficial lines
        lines_result = gpd.overlay(
            oficial_lines, overlap_buffer, how="intersection")
        # exploded result and add length
        exploded_result = lines_result.explode(index_parts=False)
        exploded_result["longitud"] = exploded_result.length
        # exploded_result = exploded_result.sort_values('longitud')
        # get lines > 20 mts
        final_result = exploded_result.query("longitud >= 20")
        # simplify results
        variable_name = "%s_2" % self.wfs.variable_wfs
        final_result.rename(columns={variable_name: 'value'}, inplace=True)
        final_result = final_result[["value", "geometry"]]
        # set crs
        final_result = final_result.to_crs('epsg:4326')
        # create file json, in localstorage
        #final_result.to_file(
        #    'media/temp/comparision_oficial.json', encodig='utf-8')
        # Return json
        return HttpResponse(final_result.to_json(), content_type='application/json')

    def compare_osm_linear_objects(self, oficial_objects, osm_objects):
        # set buffer in variables
        osm_buffer = osm_objects.set_geometry("buffered")
        wfs_buffer = oficial_objects.set_geometry("buffered")
        # Resultado B: exists in en OSM and not in WFS
        # difference overlap by buffer
        overlap_difference = gpd.overlay(
            osm_buffer, wfs_buffer, how='difference')
        osm_lineas = osm_objects.set_geometry("geometry")
        overlap_buffer = overlap_difference.set_geometry("buffered")
        # interesenction buffer with oficial lines
        lines_result = gpd.overlay(
            osm_lineas, overlap_buffer, how="intersection")
        # exploded result and add length
        exploded_result = lines_result.explode(index_parts=False)
        exploded_result["longitud"] = exploded_result.length
        # get lines > 20 mts
        final_result = exploded_result.query("longitud >= 20")
        # simplify result
        final_result = final_result.fillna(0)
        # set variable name
        variable_name = "%s_2" % self.wfs.variable_osm
        final_result.rename(
            columns={variable_name: 'value'}, inplace=True)
        final_result = final_result[["value", "geometry"]]
        # replace characters
        final_result['value'] = final_result['value'].str.replace('[', ' ')
        # set crs
        final_result = final_result.to_crs('epsg:4326')
        # create file json, in local storage
        # final_result.to_file(
        #     'media/temp/comparision_osm.json', encodig='utf-8')
        # Return json
        return HttpResponse(final_result.to_json(), content_type='application/json')

    def get_wfs_point_objects(self):
        # reproject coords bbox to wfs crs
        bbox_coords = self.get_wfs_bbox_coords()
        # Set web feature service
        wfs = WebFeatureService(url=self.wfs.url)
        # Specify the parameters for fetching the data
        params = dict(service='WFS',
                      version="1.0.0", request='GetFeature',
                      typeName=self.wfs.layer,
                      bbox=bbox_coords)
        # Generate request
        q = Request('GET', self.wfs.url, params=params).prepare().url
        # Read data from URL
        wfs_layer = gpd.read_file(q)
        # set src
        wfs_layer = wfs_layer.set_crs(self.wfs.layer_crs)
        # simplify two vars and filter
        if self.wfs.tag_wfs != 'todo':
            wfs_layer = wfs_layer.query(self.wfs.tag_wfs)
        wfs_layer = wfs_layer[[self.wfs.variable_wfs, "geometry"]]
        # Rename field variable to be able to identify it when merging into a single H3 table
        wfs_layer.rename(
            columns={self.wfs.variable_wfs: 'namewfs'}, inplace=True)
        return wfs_layer

    def get_osm_point_objects(self):
        # bbox
        south, west, north, east = self.bbox.split(',')
        # Download OSM data
        # network_type define un registes source wfs/shp
        tags = {self.wfs.tag_osm: True}
        osm_objects = ox.geometries_from_bbox(float(north), float(
            south), float(east), float(west), tags)
        # get only points
        osm_objects = osm_objects[osm_objects.geom_type == 'Point']
        # implify two vars
        osm_objects = osm_objects[[self.wfs.variable_osm, "geometry"]]
        # Rename field variable to be able to identify it when merging into a single H3 table
        osm_objects.rename(
            columns={self.wfs.variable_osm: 'nameosm'}, inplace=True)
        # create index
        osm_objects["num"] = np.arange(len(osm_objects))
        osm_objects = osm_objects.set_index("num")
        # return only edges
        return osm_objects

    def compare_point_objects(self, oficial_objects, osm_objects):
        # set projection WGS 84 to work with h3 library
        oficial_objects = oficial_objects.to_crs("EPSG:4326")
        osm_objects = osm_objects.to_crs("EPSG:4326")
        # Validate point objects in both sources
        oficial_objects = oficial_objects[oficial_objects.geom_type == 'Point']
        osm_objects = osm_objects[osm_objects.geom_type == 'Point']
        # merge sources
        total_objects = pd.concat([oficial_objects, osm_objects])
        # remove NaN elements
        total_objects = total_objects.fillna(0)
        # create the h3 objects
        hexagonal_objects = self.create_hexagonal_objects(total_objects)
        # compare lists in h3 objects
        return self.compare_hexagon_lists(hexagonal_objects)
        # return total_objects.to_json()

    def get_wfs_bbox_coords(self):
        # create dataframe and geodataframe
        south, west, north, east = self.bbox.split(',')
        bbox_df = pd.DataFrame(
            {'longitude': [west, east], 'latitude': [south, north]})
        bbox_gdf = gpd.GeoDataFrame(geometry=gpd.points_from_xy(
            bbox_df.longitude, bbox_df.latitude))
        # set and reproject crs
        bbox_gdf = bbox_gdf.set_crs('epsg:4326')
        bbox_gdf = bbox_gdf.to_crs(self.wfs.layer_crs)
        # convert to json
        bbox_json = json.loads(bbox_gdf.to_json())
        south, west = bbox_json['features'][0]['geometry']['coordinates']
        north, east = bbox_json['features'][1]['geometry']['coordinates']
        # return in string coords
        return str(south) + ',' + str(west) + ',' + str(north) + ',' + str(east)

    def create_hexagonal_objects(self, points):
        # create hexagonal index
        def lat_lng_to_h3(row):
            return h3.geo_to_h3(row.geometry.y, row.geometry.x, self.h3_level)
        points['h3'] = points.apply(lat_lng_to_h3, axis=1)
        # group osm by h3
        group_osm = (points.groupby(['h3']).nameosm.agg(list).to_frame('osm'))
        group_osm['count'] = (group_osm['osm'].apply(lambda h3: len(h3)))
        # group wfs by h3
        group_wfs = (points.groupby(['h3']).namewfs.agg(list).to_frame('wfs'))
        group_wfs['count1'] = (group_wfs['wfs'].apply(lambda h3: len(h3)))
        # merge both groups in only dataframe
        united_groups = group_osm.merge(group_wfs, on="h3", how="left")
        # Reset index so that it doesn't use the h3 fied as index
        united_groups.reset_index(level=0, inplace=True)
        # Group h3 index, since for each point generated a hexagon, with this step we select the single hexagons
        unique_h3 = united_groups.groupby(['h3']).h3.agg(
            'count').to_frame('cuenta').reset_index()
        # Merge unique h3 with dataframe that containg the grouped names: osm,wfs
        h3_objects = unique_h3.merge(united_groups, on="h3", how="left")
        # Generate the polygons to h3_objects

        def add_geometry(row):
            points = h3.h3_to_geo_boundary(row['h3'], True)
            return Polygon(points)
        h3_objects['geometry'] = (h3_objects.apply(add_geometry, axis=1))
        # Simplify the objectes with the principal fields
        return h3_objects[["h3", "osm", "wfs", "count", "geometry"]]

    def compare_hexagon_lists(self, hexagons):
        # Trabajar comparando listas OSM y WFS
        hexagons = self.compare_by_intersection(hexagons)
        hexagons = self.compare_by_find(hexagons)
        hexagons = self.compare_by_sequences(hexagons)
        compared_hexagons = self.weights_results(hexagons)
        compared_hexagons.set_crs('epsg:4326')
        # El resultado ya se puede exportar a shp o geojson, solo incluye:
        # h3 (índice del hexágono), num_puntos(el número de puntos por hexágono) y el valor (indica la clasificación del resultado)
        # h_res.to_file("h_res.shp")
        # create file json, in local storage
        # compared_hexagons.to_file(
        #     'media/temp/compared_hexagons.json', encodig='utf-8')
        # Return json
        return HttpResponse(compared_hexagons.to_json(), content_type='application/json')

    def compare_by_intersection(self, hexagons):
        # Generamos los campos que vamos a utilizar
        hexagons['osm1'] = ''
        hexagons['wfs1'] = ''
        hexagons['inters'] = ''
        # Quita los que tienen un 0, utilizando filtros
        for i in hexagons.index:
            hexagons['osm1'][i] = list(filter((0).__ne__, hexagons['osm'][i]))
            hexagons['wfs1'][i] = list(filter((0).__ne__, hexagons['wfs'][i]))

        # Primer método de comparación, por intesección de listas
        # Compara por medio de una intersección, ambas listas (registro por registro), y regresa los valores que coindicen en ambos campos
        for i in hexagons.index:
            hexagons['inters'][i] = set(hexagons['osm1'][i]).intersection(
                set(hexagons['wfs1'][i]))
        return hexagons

    def compare_by_find(self, hexagons):
        # Segundo método de comparación "find"
        # Generamos los campos que vamos a utilizar
        hexagons['en_osm'] = '-2'
        hexagons['en_wfs'] = '-2'
        hexagons['nombres'] = ''
        hexagons['osmlong'] = ''
        hexagons['wfslong'] = ''

        # Busca una sub-cadena en una cadena de caracteres
        for i in hexagons.index:
            lista1 = hexagons['osm1'][i]
            lista2 = hexagons['wfs1'][i]

        for v1, v2 in zip(lista1, lista2):
            # Encuentra WFS en OSM
            hexagons['en_osm'][i] = v1.find(v2)
            # Encuentra OSM en WFS
            hexagons['en_wfs'][i] = v2.find(v1)
            # Si la sub-cadena no está presente el programa imprimirá el valor -1

        # Calculamos la longitud de las listas, que representa el número de nombres que coinciden, el número de nombres de OSM, y el de WFS
        for k in hexagons.index:
            hexagons['nombres'][k] = len(hexagons['inters'][k])
            hexagons['osmlong'][k] = len(hexagons['osm1'][k])
            hexagons['wfslong'][k] = len(hexagons['wfs1'][k])

        # Pasamos el campo inters a tipo cadena para limpiar los conjuntos vacíos
        hexagons['inters'][k] = str((hexagons['inters'])[k])
        # Quitamos los conjuntos vacios (como ya estan en cadenas queda la palabra 'set()')
        hexagons['inters'].replace('set()', '', inplace=True)
        return hexagons

    def compare_by_sequences(self, hexagons):
        # Tercer método de comparación, librería difflib
        # Mide la similitud de las secuencias
        hexagons['compar'] = ''
        hexagons['c_osm'] = ''
        hexagons['c_wfs'] = ''
        # Se pasa la lista (los nombres en cada registro) a una cadena
        for i in hexagons.index:
            lista1 = hexagons['osm1'][i]
            lista2 = hexagons['wfs1'][i]

        hexagons['c_osm'][i] = " ".join(lista1)
        hexagons['c_wfs'][i] = " ".join(lista2)

        # Aquí se emplea la librería, similitud de secuencias
        hexagons['compar'] = hexagons.apply(lambda x: dfl.SequenceMatcher(
            None, x['c_osm'], x['c_wfs']).ratio(), axis=1)
        return hexagons

    def weights_results(self, hexagons):
        hexagons['value'] = '0'
        # Ponderación de resultados
        # Caso 1, clasificación: sin_nom
        # Caso 2, clasificación: nom_osm
        # Caso 3, clasificación: nom_wfs
        # Caso 4, clasificación: hay_nom
        # Caso 5, clasificación: sin_res

        # IMPORTANTE,se debe mantener el orden de las validaciones:
        # Caso 1, clasificación: sin_nom
        hexagons['value'].loc[(hexagons['osmlong'] == 0) & (
            hexagons['wfslong'] == 0)] = 'sin_nom'
        # Caso 2, clasificación: uno_osm
        hexagons['value'].loc[(hexagons['value'] == '0') & (
            hexagons['osmlong'] != 0) & (hexagons['wfslong'] == 0)] = 'nom_osm'
        # Caso 3, clasificación: uno_wfs
        hexagons['value'].loc[(hexagons['value'] == '0') & (
            hexagons['osmlong'] == 0) & (hexagons['wfslong'] != 0)] = 'nom_wfs'
        # Caso 4, clasificación: hay_nom
        hexagons['value'].loc[(hexagons['value'] == '0') & (
            hexagons['nombres'] != 0)] = 'hay_nom'
        hexagons['value'].loc[(hexagons['value'] == '0') & (
            hexagons['en_osm'] != -1)] = 'hay_nom'
        hexagons['value'].loc[(hexagons['value'] == '0') & (
            hexagons['en_wfs'] != -1)] = 'hay_nom'
        hexagons['value'].loc[(hexagons['value'] == '0') & (
            hexagons['compar'] >= 0.48)] = 'hay_nom'
        # Caso 5, clasificación: sin_nom
        hexagons['value'].loc[(hexagons['value'] == '0')] = 'sin_res'
        # Se seleccionan los campos de interes
        compared_hexagons = hexagons[["h3", "count", "geometry", "value"]]
        # Se renombran los campos
        compared_hexagons.rename(
            columns={'count': 'total_points'}, inplace=True)
        # Se establece el campo que indica la geometría del elemento
        compared_hexagons = compared_hexagons.set_geometry("geometry")
        return compared_hexagons


class CompareWithSHP:

    def __init__(self, layer_name, comparision_option):
        self.comparision_option = comparision_option
        self.h3_level = 7
        # get service registered
        self.shp = TemporaryShp.objects.get(name=layer_name)

    def compare(self):
        # process by layer type
        if self.shp.layer_type == 'line':
            # get oficial objects
            oficial_objects = self.get_shp_line_objects()
            # get osm objets
            osm_objects = self.get_osm_line_objects()
            # return comparision
            return self.compare_linear_objects(oficial_objects, osm_objects)
            # return osm_objects.to_json()
        elif self.shp.layer_type == 'point':
            # get oficial objects
            oficial_objects = self.get_shp_point_objects()
            # get osm objets
            osm_objects = self.get_osm_point_objects()
            # return comparision
            return self.compare_point_objects(oficial_objects, osm_objects)
        else:
            return HttpResponse(json.dumps({}), content_type='application/json')

    def get_shp_line_objects(self):
        # read file
        shp_file = gpd.read_file(r"media/temp/" + self.shp.shp_file_path)
        # simplify shp
        variable = self.shp.variable_shp.lower()
        shp_file = shp_file[[variable, "geometry"]]
        # Reproject shp file
        shp_file = shp_file.set_crs(self.shp.layer_crs)
        return shp_file

    def get_osm_line_objects(self):
        # Download OSM data
        # network_type define un registes source wfs
        # TODO rename value model
        # TODO review network type
        osm_objects = ox.graph_from_place(
            self.shp.boundary, network_type="drive")
        osm_nodes, osm_edges = ox.graph_to_gdfs(osm_objects)
        # simplify two vars
        osm_edges = osm_edges[[
            self.shp.variable_osm.lower(), "geometry"]]
        # create index
        osm_edges["num"] = np.arange(len(osm_edges))
        osm_edges = osm_edges.set_index("num")
        # return only edges
        return osm_edges

    def compare_linear_objects(self, oficial_objects, osm_objects):
        # set reprojection
        oficial_objects = oficial_objects.to_crs(self.shp.layer_crs)
        osm_objects = osm_objects.to_crs(self.shp.layer_crs)
        # create buffer
        oficial_objects["buffered"] = oficial_objects.buffer(10)
        osm_objects["buffered"] = osm_objects.buffer(10)
        # compare data
        if self.comparision_option == 'oficial':
            return self.compare_oficial_linear_objects(oficial_objects, osm_objects)
        elif self.comparision_option == 'osm':
            return self.compare_osm_linear_objects(oficial_objects, osm_objects)

    def compare_oficial_linear_objects(self, oficial_objects, osm_objects):
        # set buffer in variables
        osm_buffer = osm_objects.set_geometry("buffered")
        shp_buffer = oficial_objects.set_geometry("buffered")
        # Resultado A: exist in SHP and not in OSM
        # difference overlap by buffer
        overlap_difference = gpd.overlay(
            shp_buffer, osm_buffer, how='difference')
        oficial_lines = oficial_objects.set_geometry("geometry")
        overlap_buffer = overlap_difference.set_geometry("buffered")
        # interesenction buffer with oficial lines
        lines_result = gpd.overlay(
            oficial_lines, overlap_buffer, how="intersection")
        # exploded result and add length
        exploded_result = lines_result.explode(index_parts=False)
        exploded_result["longitud"] = exploded_result.length
        # exploded_result = exploded_result.sort_values('longitud')
        # get lines > 20 mts
        final_result = exploded_result.query("longitud >= 20")
        # set variable name
        variable_name = "%s_2" % self.shp.variable_shp.lower()
        final_result.rename(
            columns={variable_name: 'value'}, inplace=True)
        # simplify results
        final_result = final_result[["value", "geometry"]]
        final_result = final_result.to_crs('epsg:4326')
        # create file json, in local storage
        #final_result.to_file(
        #    'media/temp/comparision_oficial.json', encodig='utf-8')
        return HttpResponse(final_result.to_json(), content_type='application/json')

    def compare_osm_linear_objects(self, oficial_objects, osm_objects):
        # set buffer in variables
        osm_buffer = osm_objects.set_geometry("buffered")
        shp_buffer = oficial_objects.set_geometry("buffered")
        # Resultado B: exist in OSM and not in SHP
        # difference overlap by buffer
        overlap_difference = gpd.overlay(
            osm_buffer, shp_buffer, how='difference')
        osm_lineas = osm_objects.set_geometry("geometry")
        overlap_buffer = overlap_difference.set_geometry("buffered")
        # print (overlap_buffer)
        # interesenction buffer with oficial lines
        lines_result = gpd.overlay(
            osm_lineas, overlap_buffer, how="intersection")
        # exploded result and add length
        exploded_result = lines_result.explode(index_parts=False)
        exploded_result["longitud"] = exploded_result.length
        # get lines > 20 mts
        final_result = exploded_result.query("longitud >= 20")
        # simplify result
        final_result = final_result.fillna(0)
        # set variable name
        variable_name = "%s_2" % self.shp.variable_osm.lower()
        final_result.rename(
            columns={variable_name: 'value'}, inplace=True)
        # simplify df
        final_result = final_result[["value", "geometry"]]
        # replace characters
        final_result['value'] = final_result['value'].str.replace(
            '[', ' ')
        # set crs
        final_result = final_result.to_crs('epsg:4326')
        # create file json, in local storage
        # final_result.to_file(
        #     'media/temp/comparision_osm.json', encodig='utf-8')
        # Return json
        return HttpResponse(final_result.to_json(), content_type='application/json')

    def get_shp_point_objects(self):
        # read file
        shp_file = gpd.read_file(r"media/temp/" + self.shp.shp_file_path)
        #simplyfy shp
        variable = self.shp.variable_shp.lower()
        shp_file = shp_file[[variable, "geometry"]]
        # Rename field variable to be able to identify it when merging into a single H3 table
        shp_file.rename(
            columns={variable: 'nameshp'}, inplace=True)
        # Reproject shp file
        shp_file = shp_file.set_crs(self.shp.layer_crs)
        return shp_file

    def get_osm_point_objects(self):
        # Download OSM data
        # geocode
        # TODO tag_osm
        tags = {'place': True}
        osm_objects = ox.geometries_from_place(self.shp.boundary, tags)
        # get only points
        osm_objects = osm_objects[osm_objects.geom_type == 'Point']
        # simplify two vars
        variable = self.shp.variable_osm.lower()
        osm_objects = osm_objects[[variable, "geometry"]]
        # Rename field variable to be able to identify it when merging into a single H3 table
        osm_objects.rename(
            columns={variable: 'nameosm'}, inplace=True)
        # create index
        osm_objects["num"] = np.arange(len(osm_objects))
        osm_objects = osm_objects.set_index("num")
        return osm_objects

    def compare_point_objects(self, oficial_objects, osm_objects):
        # set projection WGS 84 to work with h3 library
        oficial_objects = oficial_objects.to_crs("EPSG:4326")
        osm_objects = osm_objects.to_crs("EPSG:4326")
        # Validate point objects in both sources
        oficial_objects = oficial_objects[oficial_objects.geom_type == 'Point']
        osm_objects = osm_objects[osm_objects.geom_type == 'Point']
        # merge sources
        total_objects = pd.concat([oficial_objects, osm_objects])
        # remove NaN elements
        total_objects = total_objects.fillna(0)
        # create the h3 objects
        hexagonal_objects = self.create_hexagonal_objects(total_objects)
        # compare lists in h3 objects
        return self.compare_hexagon_lists(hexagonal_objects)
        # return total_objects.to_json()

    def create_hexagonal_objects(self, points):
        # create hexagonal index
        def lat_lng_to_h3(row):
            return h3.geo_to_h3(row.geometry.y, row.geometry.x, self.h3_level)
        points['h3'] = points.apply(lat_lng_to_h3, axis=1)
        # group osm by h3
        group_osm = (points.groupby(['h3']).nameosm.agg(list).to_frame('osm'))
        group_osm['count'] = (group_osm['osm'].apply(lambda h3: len(h3)))
        # group shp by h3
        group_shp = (points.groupby(['h3']).nameshp.agg(list).to_frame('shp'))
        group_shp['count1'] = (group_shp['shp'].apply(lambda h3: len(h3)))
        # merge both groups in only dataframe
        united_groups = group_osm.merge(group_shp, on="h3", how="left")
        # Reset index so that it doesn't use the h3 fied as index
        united_groups.reset_index(level=0, inplace=True)
        # Group h3 index, since for each point generated a hexagon, with this step we select the single hexagons
        unique_h3 = united_groups.groupby(['h3']).h3.agg(
            'count').to_frame('cuenta').reset_index()
        # Merge unique h3 with dataframe that containg the grouped names: osm,shp
        h3_objects = unique_h3.merge(united_groups, on="h3", how="left")
        # Generate the polygons to h3_objects

        def add_geometry(row):
            points = h3.h3_to_geo_boundary(row['h3'], True)
            return Polygon(points)
        h3_objects['geometry'] = (h3_objects.apply(add_geometry, axis=1))
        # Simplify the objectes with the principal fields
        return h3_objects[["h3", "osm", "shp", "count", "geometry"]]

    def compare_hexagon_lists(self, hexagons):
        # Trabajar comparando listas OSM y WFS
        hexagons = self.compare_by_intersection(hexagons)
        hexagons = self.compare_by_find(hexagons)
        hexagons = self.compare_by_sequences(hexagons)
        compared_hexagons = self.weights_results(hexagons)
        compared_hexagons.set_crs('epsg:4326')
        # El resultado ya se puede exportar a shp o geojson, solo incluye:
        # h3 (índice del hexágono), num_puntos(el número de puntos por hexágono) y el valor (indica la clasificación del resultado)
        # h_res.to_file("h_res.shp")
        # create file json, in local storage
        # compared_hexagons.to_file(
        #     'media/temp/compared_hexagons.json', encodig='utf-8')
        # Return json
        return HttpResponse(compared_hexagons.to_json(), content_type='application/json')

    def compare_by_intersection(self, hexagons):
        # Generamos los campos que vamos a utilizar
        hexagons['osm1'] = ''
        hexagons['shp1'] = ''
        hexagons['inters'] = ''
        # Quita los que tienen un 0, utilizando filtros
        for i in hexagons.index:
            hexagons['osm1'][i] = list(filter((0).__ne__, hexagons['osm'][i]))
            hexagons['shp1'][i] = list(filter((0).__ne__, hexagons['shp'][i]))

        # Primer método de comparación, por intesección de listas
        # Compara por medio de una intersección, ambas listas (registro por registro), y regresa los valores que coindicen en ambos campos
        for i in hexagons.index:
            hexagons['inters'][i] = set(hexagons['osm1'][i]).intersection(
                set(hexagons['shp1'][i]))
        return hexagons

    def compare_by_find(self, hexagons):
        # Segundo método de comparación "find"
        # Generamos los campos que vamos a utilizar
        hexagons['en_osm'] = '-2'
        hexagons['en_shp'] = '-2'
        hexagons['nombres'] = ''
        hexagons['osmlong'] = ''
        hexagons['shplong'] = ''

        # Busca una sub-cadena en una cadena de caracteres
        for i in hexagons.index:
            lista1 = hexagons['osm1'][i]
            lista2 = hexagons['shp1'][i]

        for v1, v2 in zip(lista1, lista2):
            # Encuentra WFS en OSM
            hexagons['en_osm'][i] = v1.find(v2)
            # Encuentra OSM en SHP
            hexagons['en_shp'][i] = v2.find(v1)
            # Si la sub-cadena no está presente el programa imprimirá el valor -1

        # Calculamos la longitud de las listas, que representa el número de nombres que coinciden, el número de nombres de OSM, y el de SHP
        for k in hexagons.index:
            hexagons['nombres'][k] = len(hexagons['inters'][k])
            hexagons['osmlong'][k] = len(hexagons['osm1'][k])
            hexagons['shplong'][k] = len(hexagons['shp1'][k])

        # Pasamos el campo inters a tipo cadena para limpiar los conjuntos vacíos
        hexagons['inters'][k] = str((hexagons['inters'])[k])
        # Quitamos los conjuntos vacios (como ya estan en cadenas queda la palabra 'set()')
        hexagons['inters'].replace('set()', '', inplace=True)
        return hexagons

    def compare_by_sequences(self, hexagons):
        # Tercer método de comparación, librería difflib
        # Mide la similitud de las secuencias
        hexagons['compar'] = ''
        hexagons['c_osm'] = ''
        hexagons['c_shp'] = ''
        # Se pasa la lista (los nombres en cada registro) a una cadena
        for i in hexagons.index:
            lista1 = hexagons['osm1'][i]
            lista2 = hexagons['shp1'][i]

        hexagons['c_osm'][i] = " ".join(lista1)
        hexagons['c_shp'][i] = " ".join(lista2)

        # Aquí se emplea la librería, similitud de secuencias
        hexagons['compar'] = hexagons.apply(lambda x: dfl.SequenceMatcher(
            None, x['c_osm'], x['c_shp']).ratio(), axis=1)
        return hexagons

    def weights_results(self, hexagons):
        hexagons['value'] = '0'
        # Ponderación de resultados
        # Caso 1, clasificación: sin_nom
        # Caso 2, clasificación: nom_osm
        # Caso 3, clasificación: nom_official
        # Caso 4, clasificación: hay_nom
        # Caso 5, clasificación: sin_res

        # IMPORTANTE,se debe mantener el orden de las validaciones:
        # Caso 1, clasificación: sin_nom
        hexagons['value'].loc[(hexagons['osmlong'] == 0) & (
            hexagons['shplong'] == 0)] = 'sin_nom'
        # Caso 2, clasificación: uno_osm
        hexagons['value'].loc[(hexagons['value'] == '0') & (
            hexagons['osmlong'] != 0) & (hexagons['shplong'] == 0)] = 'nom_osm'
        # Caso 3, clasificación: uno_wfs
        hexagons['value'].loc[(hexagons['value'] == '0') & (
            hexagons['osmlong'] == 0) & (hexagons['shplong'] != 0)] = 'nom_official'
        # Caso 4, clasificación: hay_nom
        hexagons['value'].loc[(hexagons['value'] == '0') & (
            hexagons['nombres'] != 0)] = 'hay_nom'
        hexagons['value'].loc[(hexagons['value'] == '0') & (
            hexagons['en_osm'] != -1)] = 'hay_nom'
        hexagons['value'].loc[(hexagons['value'] == '0') & (
            hexagons['en_shp'] != -1)] = 'hay_nom'
        hexagons['value'].loc[(hexagons['value'] == '0') & (
            hexagons['compar'] >= 0.48)] = 'hay_nom'
        # Caso 5, clasificación: sin_nom
        hexagons['value'].loc[(hexagons['value'] == '0')] = 'sin_res'
        # Se seleccionan los campos de interes
        compared_hexagons = hexagons[["h3", "count", "geometry", "value"]]
        # Se renombran los campos
        compared_hexagons.rename(
            columns={'count': 'total_points'}, inplace=True)
        # Se establece el campo que indica la geometría del elemento
        compared_hexagons = compared_hexagons.set_geometry("geometry")
        return compared_hexagons
