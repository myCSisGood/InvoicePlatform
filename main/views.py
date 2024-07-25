# views.py
from django.shortcuts import render, redirect
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from .forms import UploadFileForm
from .models import UploadedFile
# from .bert.test import BertModel
from .models import County, District, ItemBigTag, ItemSmallTag
from django.http import JsonResponse
import io
import pandas as pd
from .graph.networks import ProductNetwork
# import networks
# import psycopg2

BUY_WITH = 1
PRODUCT_IN_PATH = 2


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


def getDistrict(request):
    countyId = request.GET.get('countyId')
    districts = District.objects.filter(county_id=countyId)
    districtList = list(districts.values('id', 'name'))
    return JsonResponse({'districts': districtList})
    ###行政區太多會往上跑的問題待修正


def _selectArea(request, pictureType):
    counties = County.objects.all()
    selectedCounty = request.session.get('selectedCounty', '')
    selectedDistrict = request.session.get('selectedDistrict', '')

    if request.method == 'POST':
        countyId = request.POST.get('county')
        districtId = request.POST.get('district')
        # request.session['selectedCounty'] = countyId
        # request.session['selectedDistrict'] = districtId
        districtName = District.objects.get(id=districtId).name
        countyName = County.objects.get(id=countyId).name
        request.session['countyName'] = countyName
        request.session['districtName'] = districtName
        request.session['selectedCounty'] = countyId
        request.session['selectedDistrict'] = districtId
        if pictureType == BUY_WITH:
            return redirect('/draw_buy_with/?step=select_path_time')
        else:
            return redirect('/draw_product_in_path/?step=select_time')

    return render(
        request, 'Area.html', {
            'counties': counties,
            'selectedCounty': selectedCounty,
            'selectedDistrict': selectedDistrict,
            'pictureType': pictureType
        }
    )


#after choosing the district narrow the stores
# def _filterSores(csvPath, districtName):
#     df = pd.read_csv(csvPath)
#     data = df[df['city_area'] == districtName]
#     stores = data['store_brand_name'].unique()
#     return stores


def _selectPathAndTime(request, pictureType):

    districtName = request.session.get('districtName', '')
    # stores = _filterSores("/Users/willa/Desktop/Graduation/300000_cleaned.csv", districtName)

    # stores = Store.objects.all()
    selectedStartTime = request.session.get('startTime', '')
    selectedEndTime = request.session.get('endTime', '')
    # selected_store_id = request.session.get('storeId', '')

    if request.method == 'POST':
        startTime = request.POST.get('start_time')
        endTime = request.POST.get('end_time')
        storeName = request.POST.get('store')
        request.session['startTime'] = startTime
        request.session['endTime'] = endTime
        request.session['store'] = storeName
        if pictureType == BUY_WITH:
            return redirect('/draw_buy_with/?step=select_tag')
        else:
            return redirect('/draw_product_in_path/?step=select_tag')
    if pictureType == BUY_WITH:
        return render(
            request,
            'PathAndTime.html',
            {
                # 'stores': stores,
                'startTime': selectedStartTime,
                'endTime': selectedEndTime,
            }
        )
    else:
        return render(
            request,
            'Time.html',
            {
                # 'stores': stores,
                'startTime': selectedStartTime,
                'endTime': selectedEndTime,
            }
        )


def _selectTag(request, pictureType):
    bigTags = ItemBigTag.objects.all()
    selectedBigTag = request.session.get('bigTagId', '')
    selectedSmallTag = request.session.get('smallTagId', '')

    if request.method == 'POST':
        bigTagId = request.POST.get('bigTag')
        smallTagId = request.POST.get('smallTag')
        bigTagName = ItemBigTag.objects.get(id=bigTagId).name
        smallTagName = ItemSmallTag.objects.get(id=smallTagId).name
        request.session['bigTagName'] = bigTagName
        request.session['smallTagName'] = smallTagName
        if pictureType == BUY_WITH:
            return redirect('/draw_buy_with/?step=display_picture')
        else:
            return redirect('/draw_product_in_path/?step=display_picture')

    return render(
        request, 'Tag.html', {
            'bigTags': bigTags,
            'bigTagId': selectedBigTag,
            'smallTagId': selectedSmallTag,
            'pictureType': pictureType
        }
    )


def _displayPic(request, pictureType, displayType=None):
    startTime = request.session.get('startTime', '')
    endTime = request.session.get('endTime', '')
    countyId = request.session.get('selectedCounty', '')
    districtId = request.session.get('selectedDistrict', '')
    countyName = request.session.get('countyName', '')
    districtName = request.session.get('districtName', '')
    store = request.session.get('store', '')
    smallTagName = request.session.get('smallTagName', '')
    counties = County.objects.all()
    districts = District.objects.filter(county_id=countyId) if countyId else []

    # paths = Path.objects.all() # Replace with actual logic to fetch paths if needed

    if request.method == 'POST':
        startTime = request.POST.get('start_time')
        endTime = request.POST.get('end_time')
        districtId = request.POST.get('district')
        store = request.POST.get('store')

        districtName = District.objects.get(id=districtId).name

        request.session['startTime'] = startTime
        request.session['endTime'] = endTime
        request.session['selectedDistrict'] = districtId
        request.session['districtName'] = districtName
        request.session['store'] = store
        # request.session['selectedPath'] = pathId

    # graph_html = _drawPic(countyName, districtName, smallTagName, startTime, endTime, store)
    # stores = _filterSores("/Users/willa/Desktop/Graduation/300000_cleaned.csv", districtName)
    if pictureType == BUY_WITH:
        return render(
            request,
            'Display.html',
            {
                'startTime': startTime,
                'endTime': endTime,
                'counties': counties,
                'districts': districts,
                # 'stores': stores,
                'selectedCounty': countyId,
                'selectedDistrict': districtId,
                'selectedPath': request.session.get('selectedPath', ''),
                # 'picture': graph_html,
                'displayType': displayType
            }
        )
    else:
        return redirect('/draw_product_in_path/?step=display_picture')


# def _drawPic(countyName, districtName, item_tag, startTime, endTime, store):
# conn = psycopg2.connect(database="mydatabase", user="postgres", password="0000", host="127.0.0.1", port="5432")
# cur = conn.cursor()
# network = ProductNetwork(cur)
# network.query(
#     county=countyName,
#     city_area=districtName,
#     item_tag=item_tag,
#     datatime_lower_bound=startTime,
#     datatime_upper_bound=endTime,
#     store_brand_name=store
# )
# result = network.execute()
# return result


def drawBuyWith(request):
    pictureType = BUY_WITH
    displayType = request.GET.get('displayType', 'Regular')
    step = request.GET.get('step', 'select_area')
    if step == 'select_area':
        return _selectArea(request, pictureType)

    elif step == 'select_path_time':
        return _selectPathAndTime(request, pictureType)

    elif step == 'select_tag':
        return _selectTag(request, pictureType)

    elif step == 'display_picture':
        return _displayPic(request, pictureType, displayType)

    return redirect('/draw_buy_with/?step=select_area')


def showInfo(request):
    displayType = request.GET.get('displayType', 'Regular')
    content = ""

    if displayType == "Articulation Points":
        content = "Information about Articulation Points."
    elif displayType == "Bridges":
        content = "Information about Bridges."
    elif displayType == "Community":
        content = "Information about Community."

    return JsonResponse({"content": content})


##防呆
##資料篩選


def drawPath(request):
    step = request.GET.get('step', 'select_area')
    pictureType = PRODUCT_IN_PATH
    if step == 'select_area':
        return _selectArea(request, pictureType)

    elif step == 'select_time':
        return _selectPathAndTime(request, pictureType)

    elif step == 'select_tag':
        return _selectTag(request, pictureType)

    return redirect('/draw_product_in_path/?step=select_area')


def analyze(request):
    return render(request, 'Analysis.html')


def displayOvertime(request):
    return render(request, 'Overtime.html')


def getDeeperInsight(request):
    table = [
        {
            'product': '*麒麟*一番搾500cc罐',
            'counts': 76,
            'percentage': '1.890077'
        },
        {
            'product': '(A)*台灣啤酒500cc玻璃瓶',
            'counts': 65,
            'percentage': '1.616513'
        },
        # getData()
    ]

    context = {'table': table}
    return render(request, 'DeeperInsight.html', context)
