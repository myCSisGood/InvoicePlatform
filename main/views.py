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
from .Graph.networks import ProductNetwork
import networks
import psycopg2
from django.db import connection

BUY_WITH = 1
PRODUCT_IN_PATH = 2
RFM = 3
RFM_WITH_PRODUCT = 4


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
    bigtag = request.GET.get('bigtag')
    smallTags = ItemSmallTag.objects.filter(bigTag__name=bigtag)
    smallTagList = list(smallTags.values('id', 'name'))
    return JsonResponse({'smallTags': smallTagList})


    ###directly select smallTag and Product?
def getProducts(request):
    smallTag = request.GET.get('smallTag')
    with connection.cursor() as cursor:
        cursor.execute("SELECT DISTINCT item_name FROM test WHERE item_tag = %s", [smallTag])
        rows = cursor.fetchall()
    products = [row[0] for row in rows]
    for p in products:
        print(p)
    return JsonResponse({'products': products})


###行政區太多會往上跑的問題待修正###
def getDistrict(request):
    countyId = request.GET.get('countyId')
    districts = District.objects.filter(county_id=countyId)
    districtList = list(districts.values('id', 'name'))
    return JsonResponse({'districts': districtList})


def _selectArea(request, pictureType):
    counties = County.objects.all()
    selectedCounty = request.session.get('selectedCounty', '')
    # selectedDistrict = request.session.get('selectedDistrict', '')

    if request.method == 'POST':
        county = request.POST.get('county')
        request.session['selectedCounty'] = county
        if pictureType == BUY_WITH:
            return redirect('/draw_buy_with/?step=select_path_time')
        elif pictureType == PRODUCT_IN_PATH:
            return redirect('/draw_product_in_path/?step=select_time')
        elif pictureType == RFM:
            return redirect('/rfm/?step=select_path_time')
        elif pictureType == RFM_WITH_PRODUCT:
            return redirect('/rfm_with_product/?step=select_path_time')

    return render(
        request,
        'Area.html',
        {
            'counties': counties,
            'selectedCounty': selectedCounty,
            # 'selectedDistrict': selectedDistrict,
            'pictureType': pictureType
        }
    )


###這邊會改成有分類的前幾+交易量前幾###
def _filterStores(countyName, districtName=None):
    print(countyName)
    if districtName:
        with connection.cursor() as cursor:
            cursor.execute(
                "SELECT DISTINCT store_brand_name FROM test WHERE county = %s AND city_area = %s",
                [countyName, districtName]
            )
            rows = cursor.fetchall()
    else:
        with connection.cursor() as cursor:
            cursor.execute("SELECT DISTINCT store_brand_name FROM test WHERE county = %s", [countyName])
            rows = cursor.fetchall()
    storeBrands = [row[0] for row in rows]

    return storeBrands


def _filterBigTags(request):
    countyName = request.session.get('selectedCounty', '')
    districtName = request.session.get('districtName', '')
    selectedStartTime = request.session.get('startTime', '')
    selectedEndTime = request.session.get('endTime', '')
    selectedStore = request.session.get('store', '')
    print(districtName)
    query = "SELECT DISTINCT item_tag FROM test WHERE county = %s"
    params = [countyName]

    if districtName:
        query += " AND city_area = %s"
        params.append(districtName)

    if selectedStartTime:
        query += " AND datetime >= %s"
        params.append(selectedStartTime)

    if selectedEndTime:
        query += " AND datetime <= %s"
        params.append(selectedEndTime)

    if selectedStore:
        query += " AND store_brand_name = %s"
        params.append(selectedStore)

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    smallTags = [row[0] for row in rows]
    bigTags = set()
    ###暫時反向尋找，之後建立大標籤之欄位###
    for tag in smallTags:
        smallTag = ItemSmallTag.objects.get(name=tag)
        bigTags.add(smallTag.bigTag.name)

    bigTags = list(bigTags)
    return bigTags


def _selectPathAndTime(request, pictureType):
    countyName = request.session.get('selectedCounty', '')
    districtName = request.session.get('districtName', '')
    stores = _filterStores(countyName)

    # stores = Store.objects.all()
    selectedStartTime = request.session.get('startTime', '')
    selectedEndTime = request.session.get('endTime', '')
    selectedStore = request.session.get('store', '')
    if request.method == 'POST':
        startTime = request.POST.get('start_time')
        endTime = request.POST.get('end_time')
        storeName = request.POST.get('store')
        request.session['startTime'] = startTime
        request.session['endTime'] = endTime
        request.session['store'] = storeName
        if pictureType == BUY_WITH:
            return redirect('/draw_buy_with/?step=select_tag')
        elif pictureType == PRODUCT_IN_PATH:
            return redirect('/draw_product_in_path/?step=select_tag')
        elif pictureType == RFM:
            return redirect('/rfm/?step=display_picture')
        elif pictureType == RFM_WITH_PRODUCT:
            return redirect('/rfm_with_product/?step=select_tag')
    if pictureType == PRODUCT_IN_PATH:
        return render(
            request, 'Time.html', {
                'stores': stores,
                'startTime': selectedStartTime,
                'endTime': selectedEndTime,
            }
        )
    else:
        return render(
            request, 'PathAndTime.html', {
                'stores': stores,
                'startTime': selectedStartTime,
                'endTime': selectedEndTime,
                'pictureType': pictureType,
            }
        )


def _selectTag(request, pictureType):
    bigTags = _filterBigTags(request)
    selectedBigTag = request.session.get('bigTag', '')
    selectedSmallTag = request.session.get('smallTag', '')

    if request.method == 'POST':
        bigTag = request.POST.get('bigTag')
        smallTag = request.POST.get('smallTag')
        request.session['bigTag'] = bigTag
        request.session['smallTag'] = smallTag
        if pictureType == BUY_WITH:
            return redirect('/draw_buy_with/?step=display_picture')
        elif pictureType == PRODUCT_IN_PATH:
            return redirect('/draw_product_in_path/?step=display_picture')
        elif pictureType == RFM_WITH_PRODUCT:
            return redirect('/rfm_with_product/?step=display_picture')
    return render(
        request, 'Tag.html', {
            'bigTags': bigTags,
            'bigTagId': selectedBigTag,
            'smallTagId': selectedSmallTag,
            'pictureType': BUY_WITH
        }
    )


def _displayPic(request, displayType, pictureType):
    startTime = request.session.get('startTime', '')
    endTime = request.session.get('endTime', '')
    countyName = request.session.get('selectedCounty', '')
    districtName = request.session.get('selectedDistrict', '')
    store = request.session.get('store', '')
    smallTag = request.session.get('smallTag', '')
    districts = District.objects.filter(county__name=countyName) if countyName else []

    # paths = Path.objects.all() # Replace with actual logic to fetch paths if needed
    relationship, articulationPoint, communities = _drawPic(
        countyName, districtName, smallTag, startTime, endTime, store
    )
    stores = _filterStores(districtName)
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

    if pictureType == BUY_WITH:
        return render(
            request, 'Display.html', {
                'startTime': startTime,
                'endTime': endTime,
                'counties': counties,
                'districts': districts,
                'selectedCounty': countyId,
                'selectedDistrict': districtId,
                'selectedPath': request.session.get('selectedPath', ''),
                'displayType': displayType,
                'stores': stores,
                'picture_regular': relationship,
                'picture_articulation': articulationPoint,
                'picture_community': communities,
            }
        )
    else:
        return render(
            request, 'ProductInPath.html', {
                'startTime': startTime,
                'endTime': endTime,
                'counties': counties,
                'districts': districts,
                'stores': stores,
                'selectedCounty': countyId,
                'selectedDistrict': districtId,
                'selectedPath': request.session.get('selectedPath', ''),
                'picture': graphHtml,
            }
        )


def _drawPic(countyName, smallTag, startTime, endTime, store=None, districtName=None):

    network = ProductNetwork(username='admin', network_name='啤酒網路圖')
    network.query(
        county=countyName,
        city_area=districtName,
        item_tag=smallTag,
        datetime_lower_bound=startTime,
        datetime_upper_bound=endTime,
        store_brand_name=store
    )
    network.execute_query()
    network.analysis(limits=100)
    network.create_network()
    relationship, articulationPoint, communities = network.vis_all_graph()
    return relationship, articulationPoint, communities


def drawBuyWith(request):
    displayType = request.GET.get('displayType', 'Regular')
    step = request.GET.get('step', 'select_area')
    pictureType = BUY_WITH
    if step == 'select_area':
        return _selectArea(request, pictureType)

    elif step == 'select_path_time':
        return _selectPathAndTime(request, pictureType)

    elif step == 'select_tag':
        return _selectTag(request, pictureType)

    elif step == 'display_picture':
        return _displayPic(request, displayType, pictureType)

    return redirect('/draw_buy_with/?step=select_area')


def showInfo(request):
    displayType = request.GET.get('displayType', 'Regular')
    content = ""

    if displayType == "Articulation Points":
        content = "Information about Articulation Points."
    elif displayType == "Community":
        content = "Information about Community."
    else:
        content = "Information about Regular."

    return JsonResponse({"content": content})


##防呆
##資料篩選


def drawPath(request):
    displayType = request.GET.get('displayType', 'Regular')
    step = request.GET.get('step', 'select_area')
    pictureType = PRODUCT_IN_PATH
    if step == 'select_area':
        return _selectArea(request, pictureType)

    elif step == 'select_time':
        selectedStartTime = request.session.get('startTime', '')
        selectedEndTime = request.session.get('endTime', '')

        if request.method == 'POST':
            startTime = request.POST.get('start_time')
            endTime = request.POST.get('end_time')
            request.session['startTime'] = startTime
            request.session['endTime'] = endTime

            return redirect('/draw_product_in_path/?step=select_tag')

        return render(request, 'Time.html', {
            'startTime': selectedStartTime,
            'endTime': selectedEndTime,
        })

    elif step == 'select_tag':
        return _selectTag(request, pictureType)

    elif step == 'display_picture':
        return _displayPic(request, displayType, pictureType)

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


def drawRFM(request):
    step = request.GET.get('step', 'select_area')
    pictureType = RFM
    if step == 'select_area':
        return _selectArea(request, pictureType)

    elif step == 'select_path_time':
        return _selectPathAndTime(request, pictureType)

    elif step == 'display_picture':
        return _displayRFM(request)

    return redirect('/rfm/?step=select_area')


def drawRFMwithProduct(request):
    step = request.GET.get('step', 'select_area')
    pictureType = RFM_WITH_PRODUCT
    if step == 'select_area':
        return _selectArea(request, pictureType)

    elif step == 'select_path_time':
        return _selectPathAndTime(request, pictureType)

    elif step == 'select_tag':
        return _selectTag(request, pictureType)

    elif step == 'display_picture':
        return _displayRFM(request)

    return redirect('/rfm_with_product/?step=select_area')


def _displayRFM(request):
    rfms = [
        "Champions", "Loyal Accounts", "Low Spenders", "Potential Loyalist", "Promising", "New Active Accounts",
        "Need Attention", "About to Sleep", "At Risk", "Lost"
    ]

    if request.method == "POST":
        rfmType = request.POST.get('district', 'Potential Loyalist')
    else:
        rfmType = 'Potential Loyalist'

    context = {
        'rfmType': rfmType,
        'rfms': rfms,
    }

    return render(request, 'RFM.html', context)
