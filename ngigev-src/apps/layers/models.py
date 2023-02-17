from django.db import models
OBJECT_TYPES = (
    ('point', 'Puntos'),
    ('line', 'Lineas'),
)


class WFSService(models.Model):
    name = models.CharField('Nombre', max_length=100)
    country = models.CharField('Pais', max_length=50)
    url = models.CharField('Url', max_length=200)
    layer = models.CharField('Nombre de Capa', max_length=50)
    layer_crs = models.CharField('CRS de la capa', max_length=10)
    layer_type = models.CharField(
        'Tipo de Objetos', max_length=10, choices=OBJECT_TYPES)
    tag_wfs = models.CharField(
        'Tag filtro en la Capa', max_length=50, default='ninguno')
    variable_wfs = models.CharField('Variable a Comparar WFS*', max_length=50)
    tag_osm = models.CharField(
        'Tag de objetos OSM', max_length=50, default='place')
    variable_osm = models.CharField(
        'Variable a comparar de OSM', max_length=50)

    class Meta:
        verbose_name = 'Servicio WFS'
        verbose_name_plural = 'Servicios WFS'

    def __str__(self):
        return "%s %s" % (self.name, self.country)

    def get_full_name(self):
        return "%s %s" % (self.name, self.country)


class TemporaryShp(models.Model):
    name = models.CharField('Nombre', max_length=100)
    shp_file_path = models.CharField('Archivos Shp', max_length=200)
    layer_crs = models.CharField('EPSG', max_length=10)
    layer_type = models.CharField(
        'Tipo de Objetos', max_length=10, choices=OBJECT_TYPES)
    variable_shp = models.CharField('Variable SHP', max_length=50)
    boundary = models.CharField('Limite administrativo OSM', max_length=50)
    tag_osm = models.CharField(
        'Tag de objetos OSM', max_length=50, default='place')
    variable_osm = models.CharField(
        'Variable a comparar de OSM', max_length=50)

    class Meta:
        verbose_name = 'SHP Temporal'
        verbose_name_plural = 'SHP Temporales'

    def __str__(self):
        return "%s" % (self.name)

    def get_full_name(self):
        return "%s" % (self.name)
