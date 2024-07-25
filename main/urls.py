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
    path('rfm/', views.drawRFM, name='drawRFM'),
    path('rfm_with_product/', views.drawRFMwithProduct, name='drawRFMwithProduct'),
    path('info/', views.showInfo, name='showInfo'),
    path('deeper_insight/', views.getDeeperInsight, name='getDeeperInsight'),
    path('analysis/', views.analyze, name='analyze'),
    path('display_overtime/', views.displayOvertime, name='displayOvertime'),
]
