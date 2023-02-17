from django.urls import path
from . import views

app_name = 'layers'

urlpatterns = [
    path('services-wfs/', views.WFSServicesView.as_view(), name='wfs'),
    path('shp/load/', views.LoadTemporaryShpView.as_view(), name='load_shp'),
    path('wfs/load/<int:pk>/<str:bbox>/', views.LoadWFSView.as_view(), name='load_wfs'),
    path('osm/load/<slug:source>/<int:pk>/<str:bbox>/', views.LoadOSMPoints.as_view(), name='load_points'),
    path('osm/load/<slug:source>/<str:name>/<str:bbox>/', views.LoadOSMPoints.as_view(), name='load_points'),
]
