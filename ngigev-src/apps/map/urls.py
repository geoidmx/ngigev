from django.urls import path
from . import views

app_name = 'map'

urlpatterns = [
    path('', views.MapView.as_view(), name='map'),
    path('map/compare/<slug:source>/<int:pk>/<str:option>/<str:bbox>/', views.CompareDataView.as_view(), name='compare_data'),
    path('map/compare/<slug:source>/<str:name>/<str:option>/<str:bbox>/', views.CompareDataView.as_view(), name='compare_data'),
]
