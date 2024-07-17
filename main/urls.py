from django.urls import path

from . import views

app_name = 'main'
urlpatterns = [
    path('mainpage/', views.getMainpage, name='getMainpage'),
    path('file/upload/', views.uploadFile, name='uploadFile'),
    # path('menu/', views.getMenupage, name='getMenupage'),
    path('area/', views.getAreaMenu, name='getAreaMenu'),
    path('district/', views.getDistrict, name='getDistrict'),
    # path('select_area/', views.selectArea, name='selectArea'),
    path('path&time/', views.getPTimeMenu, name='getPTimeMenu'),
    path('product/', views.getProductMenu, name='getProductMenu'),
    path('tags/', views.getSmallTags, name='getSmallTags'),
    path('product/', views.getProducts, name='getProducts'),
    path('draw_buy_with/', views.drawBuyWith, name='drawBuyWith'),
]
