# views.py
from django.shortcuts import render, redirect
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from .forms import UploadFileForm
from .models import UploadedFile
from .Bert.test import BertModel
from .models import County, District, ItemBigTag, ItemSmallTag
from django.http import JsonResponse
import io
import pandas as pd


def uploadFile(request):
    if request.method == 'POST':
        form = UploadFileForm(request.POST, request.FILES)
        if form.is_valid():
            file = form.cleaned_data['file']
            if file.name.endswith('.csv'):
                df = pd.read_csv(file)
                b = BertModel()
                df = b.addItemTag(df)
                buffer = io.StringIO()
                df.to_csv(buffer, index=False)
                content = buffer.getvalue()
            else:
                df = pd.read_excel(file)
                b = BertModel()
                df = b.addItemTag(df)
                buffer = io.BytesIO()
                df.to_excel(buffer, index=False, engine='openpyxl')
                content = buffer.getvalue()

            fs = FileSystemStorage(location=settings.MEDIA_ROOT)
            filename = fs.save(
                file.name, io.BytesIO(content.encode('utf-8') if file.name.endswith('.csv') else content)
            )
            UploadedFile.objects.create(user=request.user, file_name=filename)
            fileUrl = fs.url(filename)
            return render(request, 'UploadFile.html', {'form': form, 'fileUrl': fileUrl})
    else:
        form = UploadFileForm()
    return render(request, 'UploadFile.html', {'form': form})


    ###行政區太多會往上跑的問題待修正
def getMainpage(request):
    return render(request, 'Mainpage.html')


def getProductMenu(request):
    bigTags = ItemBigTag.objects.all()
    smallTags = ItemSmallTag.objects.all()

    return render(request, 'Tag.html', {'bigTags': bigTags, 'smallTags': smallTags})


def getSmallTags(request):
    bigId = request.GET.get('bigId')
    smallTags = ItemSmallTag.objects.filter(bigTag_id=bigId)
    smallTagList = list(smallTags.values('id', 'name'))
    return JsonResponse({'smallTags': smallTagList})


    ###directly select smallTag and Product?
def getProducts(request):
    smallId = request.GET.get('smallId')
    productList = []
    # products = Product.objects.filter(smallTag_id=smallId)
    # productList = list(products.values('id', 'name'))
    return JsonResponse({'products': productList})


def getPTimeMenu(request):
    return render(request, 'PathAndTime.html')


def getAreaMenu(request):
    counties = County.objects.all()
    return render(request, 'Area.html', {'counties': counties, 'districts': []})


def getDistrict(request):
    countyId = request.GET.get('countyId')
    districts = District.objects.filter(county_id=countyId)
    districtList = list(districts.values('id', 'name'))
    return JsonResponse({'districts': districtList})
    ###行政區太多會往上跑的問題待修正


def selectArea(request):
    if request.method == 'POST':
        countyId = request.POST.get('county')
        districtId = request.POST.get('district')
        request.session['selectedCounty'] = countyId
        request.session['selectedDistrict'] = districtId


def selectPathAndTime(request):
    if request.method == 'POST':
        startTime = request.POST.get('start_time')
        endTime = request.POST.get('end_time')
        # storeId = request.POST.get('store')
        request.session['startTime'] = startTime
        request.session['endTime'] = endTime
        # request.session['storeId'] = storeId
        return redirect('selectTag')


def selectTag(request):
    if request.method == 'POST':
        bigTagId = request.POST.get('bigTag')
        smallTagId = request.POST.get('smallTag')
        request.session['bigTagId'] = bigTagId
        request.session['smallTagId'] = smallTagId
        return redirect('finalStep') # Redirect to the final step or another view


def drawBuyWith(request):
    step = request.GET.get('step', 'select_area')

    if step == 'select_area':
        counties = County.objects.all()
        selectedCounty = request.session.get('selectedCounty', '')
        selectedDistrict = request.session.get('selectedDistrict', '')

        if request.method == 'POST':
            countyId = request.POST.get('county')
            districtId = request.POST.get('district')
            request.session['selectedCounty'] = countyId
            request.session['selectedDistrict'] = districtId
            return redirect('/draw_buy_with/?step=select_path_time')

        return render(
            request, 'Area.html', {
                'counties': counties,
                'selectedCounty': selectedCounty,
                'selectedDistrict': selectedDistrict
            }
        )

    elif step == 'select_path_time':
        # stores = Store.objects.all()
        selectedStartTime = request.session.get('startTime', '')
        selectedEndTime = request.session.get('endTime', '')
        # selected_store_id = request.session.get('storeId', '')

        if request.method == 'POST':
            startTime = request.POST.get('start_time')
            endTime = request.POST.get('end_time')
            # store_id = request.POST.get('store')
            request.session['startTime'] = startTime
            request.session['endTime'] = endTime
            # request.session['storeId'] = store_id
            return redirect('/draw_buy_with/?step=select_tag')

        return render(
            request,
            'PathAndTime.html',
            {
                # 'stores': stores,
                'startTime': selectedStartTime,
                'endTime': selectedEndTime,
                # 'storeId': selected_store_id
            }
        )

    elif step == 'select_tag':
        bigTags = ItemBigTag.objects.all()
        selectedBigTag = request.session.get('bigTagId', '')
        selectedSmallTag = request.session.get('smallTagId', '')

        if request.method == 'POST':
            bigTagId = request.POST.get('bigTag')
            smallTagId = request.POST.get('smallTag')
            request.session['bigTagId'] = bigTagId
            request.session['smallTagId'] = smallTagId
            print("okokokokookko")
            # return redirect('/final_step/') # Replace with the actual final step URL

        return render(
            request, 'Tag.html', {
                'bigTags': bigTags,
                'bigTagId': selectedBigTag,
                'smallTagId': selectedSmallTag
            }
        )

    return redirect('/draw_buy_with/?step=select_area')


##防呆
##資料篩選
