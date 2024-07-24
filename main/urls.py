from django.urls import path

from . import views

app_name = 'main'
urlpatterns = [
    path('mainpage/', views.getMainpage, name='getMainpage'),
    path('file/upload/', views.uploadFile, name='uploadFile'),
    path('district/', views.getDistrict, name='getDistrict'),
    path('tags/', views.getSmallTags, name='getSmallTags'),
    path('product/', views.getProducts, name='getProducts'),
    path('draw_buy_with/', views.drawBuyWith, name='drawBuyWith'),
    path('draw_product_in_path/', views.drawPath, name='drawPath'),
    path('display_and_revise/', views.displayPicture, name='displayPicture'),
    path('info/', views.showInfo, name='showInfo'),
]
