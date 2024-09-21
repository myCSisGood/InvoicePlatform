# views.py
from django.shortcuts import render, redirect
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.utils.dateparse import parse_date
from .forms import UploadFileForm
from django.http import HttpResponse
from .models import UploadedFile
from .Bert.test import BertModel
from .models import County, District, ItemBigTag, ItemSmallTag
from django.http import JsonResponse
import io
import pandas as pd
from .Graph.networks import ProductNetwork
from .Graph.chatbot import Chatbot
import networks
import psycopg2
from django.db import connection
from main import PathList
from decimal import Decimal

BUY_WITH = 1
PRODUCT_IN_PATH = 2
RFM = 3
RFM_WITH_PRODUCT = 4
COUNTRY_DICT = {
    "南投縣": "Nantou",
    "嘉義市": "ChiaYiCity",
    "新北市": "NewTaipei",
    "新竹市": "HsinChuCity",
    "新竹縣": "HsinChuCounty",
    "桃園市": "TaoYuan",
    "澎湖縣": "PengHo",
    "臺中市": "Taichung",
    "臺北市": "Taipei",
    "臺南市": "Tainan",
    "臺東縣": "Taitung",
    "花蓮縣": "HuaLien",
    "苗栗縣": "MiaoLi",
    "金門縣": "KingMen",
    "雲林縣": "YuinLin",
    "高雄市": "KaoHsung",
    "嘉義縣": "ChiaYiCounty",
    "基隆市": "KeeLung",
    "宜蘭縣": "YiLan",
    "屏東縣": "PingTung",
    "彰化縣": "ChungHua",
    "nan": "nan",
}


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
        cursor.execute(
            """
            SELECT item_name, COUNT(*) 
            FROM test 
            WHERE item_tag = %s 
            GROUP BY item_name
        """, [smallTag]
        )
        rows = cursor.fetchall()

    # 將產品名稱和對應的資料數量一起返回
    products = [{'name': row[0], 'count': row[1]} for row in rows]
    return JsonResponse({'products': products})


###行政區太多會往上跑的問題待修正###
def getDistrict(request):
    county = request.GET.get('county')
    districts = District.objects.filter(county__name=county)
    districtList = list(districts.values('id', 'name'))
    return JsonResponse({'districts': districtList})


def _selectArea(request, pictureType):
    counties = County.objects.all()
    selectedCounty = request.session.get('selectedCounty', '')
    errorMessage = ""

    if request.method == 'POST':
        county = request.POST.get('county')
        if not county:
            errorMessage = "請選擇縣/市"
        else:
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
        request, 'Area.html', {
            'counties': counties,
            'selectedCounty': selectedCounty,
            'pictureType': pictureType,
            'errorMessage': errorMessage
        }
    )


###這邊會改成有分類的前幾+交易量前幾###
# def _filterStores(countyName, districtName=None):
#     if districtName:
#         with connection.cursor() as cursor:
#             cursor.execute(
#                 "SELECT DISTINCT store_brand_name FROM test WHERE county = %s AND city_area = %s",
#                 [countyName, districtName]
#             )
#             rows = cursor.fetchall()
#     else:
#         with connection.cursor() as cursor:
#             cursor.execute("SELECT DISTINCT store_brand_name FROM test WHERE county = %s", [countyName])
#             rows = cursor.fetchall()
#     storeBrands = [row[0] for row in rows]

#     return storeBrands


def _filterDistrictsStore(countyName, storeList, itemTag, product=None, minStoreCount=10):
    county = COUNTRY_DICT[countyName]
    stores = tuple(storeList)

    # Base SQL query with necessary joins
    query = f"""
        SELECT store_brand_name, COUNT(*) as store_count
        FROM {county}
        WHERE store_brand_name IN {stores}
        AND a_item_tag = %s
    """

    # If a product is provided, add a condition to filter by product
    if product:
        if isinstance(product, list):
            query += f" AND a_item_name IN {tuple(product)}"
        else:
            query += f" AND  a_item_name = {product}"

    query += """
        GROUP BY store_brand_name
        HAVING COUNT(*) > %s
    """

    # Prepare parameters for query execution
    params = [itemTag]
    params.append(minStoreCount)

    with connection.cursor() as cursor:
        cursor.execute(query, params) # Pass the parameters dynamically
        result = cursor.fetchall()

    existingStores = [row[0] for row in result] # Get store_brand_name from result

    return existingStores


def _filterDistrict(countyName):
    if countyName:
        districtList = District.objects.filter(county__name=countyName).values_list('name', flat=True)
        return list(districtList)
    return []


def _filterBigTags(request):
    countyName = request.session.get('selectedCounty', '')
    districtName = request.session.get('districtName', '')
    selectedStartTime = request.session.get('startTime', '')
    selectedEndTime = request.session.get('endTime', '')
    # selectedStore = request.session.get('store', '')
    storeTypeList = request.session.get('storeTypeList', '')

    query = "SELECT DISTINCT item_tag FROM test WHERE county = %s"
    params = [countyName]

    # if districtName:
    #     query += " AND city_area = %s"
    #     params.append(districtName)

    if selectedStartTime:
        query += " AND datetime >= %s::date"
        params.append(f"{selectedStartTime}-01")

    if selectedEndTime:
        query += " AND datetime < (%s::date + interval '1 month')"
        params.append(f"{selectedEndTime}-01")

    if storeTypeList:
        # 使用 IN 语句匹配列表中的任意值
        query += " AND store_brand_name IN %s"
        params.append(tuple(storeTypeList))

    with connection.cursor() as cursor:
        cursor.execute(query, params)
        rows = cursor.fetchall()

    smallTags = [row[0] for row in rows]
    ###暫時反向尋找，之後建立大標籤之欄位###
    bigTags = ItemSmallTag.objects.filter(name__in=smallTags).values_list('bigTag__name', flat=True).distinct()
    bigTagsList = list(bigTags)
    return bigTagsList


def _selectPathAndTime(request, pictureType):
    countyName = request.session.get('selectedCounty', '')
    districtName = request.session.get('districtName', '')
    # stores = _filterStores(countyName)

    selectedStartTime = request.session.get('startTime', '')
    selectedEndTime = request.session.get('endTime', '')
    storeType = request.session.get('storeType', '')
    storeTypeList = request.session.get('storeTypeList', '')
    errorMessage = request.GET.get('error_message', '')

    if request.method == 'POST':
        startTime = request.POST.get('start_time')
        endTime = request.POST.get('end_time')
        storeType = request.POST.get('store')
        storeTypeList = PathList.getStoreList(storeType)
        request.session['startTime'] = startTime
        request.session['endTime'] = endTime
        request.session['storeType'] = storeType
        request.session['storeTypeList'] = storeTypeList

        startDate = parse_date(startTime)
        endDate = parse_date(endTime)

        if startDate and endDate and startDate >= endDate:
            errorMessage = "開始時間必須早於結束時間"
        else:
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
            request,
            'Time.html',
            {
                # 'stores': stores,
                'startTime': selectedStartTime,
                'endTime': selectedEndTime,
                'errorMessage': errorMessage,
            }
        )
    else:
        return render(
            request,
            'PathAndTime.html',
            {
                # 'stores': stores,
                'startTime': selectedStartTime,
                'endTime': selectedEndTime,
                'pictureType': pictureType,
                'errorMessage': errorMessage,
            }
        )


def _selectTag(request, pictureType):
    bigTags = _filterBigTags(request)
    selectedBigTag = request.session.get('bigTag', '')
    selectedSmallTag = request.session.get('smallTag', '')
    selectedProduct = request.session.get('product', '')

    if request.method == 'POST':
        bigTag = request.POST.get('bigTag')
        smallTag = request.POST.get('smallTag')
        selectedProducts = request.POST.get('selectedProducts')
        if selectedProducts:
            # 將逗號分隔的產品列表轉為 Python 列表
            productList = selectedProducts.split(',')
            request.session['productList'] = productList
        # product = request.POST.get('product')
        request.session['bigTag'] = bigTag
        request.session['smallTag'] = smallTag

        if not smallTag:
            errorMessage = '請選擇子分類'
            return redirect(f'/draw_buy_with/?step=select_tag&error_message={errorMessage}')

        if pictureType == BUY_WITH:
            return redirect('/draw_buy_with/?step=display_picture')
        elif pictureType == PRODUCT_IN_PATH:
            return redirect('/draw_product_in_path/?step=display_picture')
        elif pictureType == RFM_WITH_PRODUCT:
            return redirect('/rfm_with_product/?step=display_picture')

    bigTags = _filterBigTags(request)
    if not bigTags:
        return redirect('/draw_buy_with/?step=select_path_time&error_message=此區間無資料，請重新選擇。')
    errorMessage = request.GET.get('errorMessage', '')
    return render(
        request, 'Tag.html', {
            'bigTags': bigTags,
            'bigTag': selectedBigTag,
            'smallTag': selectedSmallTag,
            'product': selectedProduct,
            'pictureType': pictureType,
            'errorMessage': errorMessage
        }
    )


def _displayPathPic(request):
    startTime = request.session.get('startTime', '')
    endTime = request.session.get('endTime', '')
    countyName = request.session.get('selectedCounty', '')
    district = request.session.get('selectedDistrict', '') # narrow down 才有
    smallTag = request.session.get('smallTag', '')
    productList = request.session.get('productList', '')
    # product = request.session.get('product', '')
    orderBy = request.GET.get('order_by', 'TOTAL_QUANTITY') # Get order by parameter
    df = _drawPic(countyName, smallTag, PRODUCT_IN_PATH, startTime, endTime, productList=productList)

    # Sort the dataframe based on the selected option
    df = df.sort_values(by=orderBy, ascending=False)

    dfDict = {
        key: [float(value) if isinstance(value, Decimal) else value for value in values]
        for key, values in df.to_dict(orient='list').items()
    }

    topList = list(zip(dfDict['STORE_NAME'], dfDict[orderBy]))
    sortedList = sorted(topList, key=lambda x: x[1], reverse=True)

    topStores = [store for store, _ in sortedList[:10]]
    topValues = [value for _, value in sortedList[:10]]

    data = list(
        zip(
            dfDict.get('STORE_NAME', []), dfDict.get('TOTAL_QUANTITY', []), dfDict.get('TOTAL_PROFIT', []),
            dfDict.get('PROFIT_PER_UNIT', []), dfDict.get('NUMBER_OF_SALESRECORD', []),
            dfDict.get('PROFIT_PER_SALES', [])
        )
    )

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'top_10_stores': topStores, 'top_10_quantities': topValues, 'data': data})

    title = productList if productList else smallTag

    return render(
        request, 'ProductInPath.html', {
            'df': dfDict,
            'title': title,
            'titleList': productList,
            'top_10_stores': topStores,
            'top_10_quantities': topValues,
            'data': data,
        }
    )


def _displayPic(request, pictureType, displayType=None):
    startTime = request.session.get('startTime', '')
    endTime = request.session.get('endTime', '')
    countyName = request.session.get('selectedCounty', '')
    if pictureType in (RFM_WITH_PRODUCT, RFM):
        segment = request.session.get('segment', 'Potential Loyalist')
    else:
        segment = request.session.get('segment', '')

    district = request.session.get('selectedDistrict', '') # narrow down 才有
    storeType = request.session.get('storeType', '')
    storeTypeList = request.session.get('storeTypeList', '')
    smallTag = request.session.get('smallTag', '')
    productList = request.session.get('productList', '')
    limit = request.session.get('limit', '')

    districtList = _filterDistrict(countyName)
    storesToQuery = storeTypeList
    # stores = _filterStores(districtName)
    if storeTypeList:
        storeCanBeChoose = _filterDistrictsStore(
            countyName=countyName, storeList=storeTypeList, itemTag=smallTag, product=productList
        )
    else:
        storeCanBeChoose = None
    if request.method == 'POST':
        startTime = request.POST.get('start_time')
        endTime = request.POST.get('end_time')
        district = request.POST.get('district')
        storesToQuery = request.POST.get('store')
        segment = request.POST.get('segment')
        limit = request.POST.get('limit')
        # districtName = District.objects.get(id=districtId).name
        request.session['startTime'] = startTime
        request.session['endTime'] = endTime
        request.session['selectedDistrict'] = district
        # request.session['districtName'] = districtName
        request.session['store'] = storesToQuery
        request.session['segment'] = segment
        request.session['limit'] = limit
        # request.session['selectedPath'] = pathId

    relationship, articulationPoint, communities, df = _drawPic(
        countyName,
        smallTag,
        pictureType,
        startTime,
        endTime,
        productList,
        storesToQuery,
        district, #narrow down
        segment,
        limit
    )
    nodes, edges = _getNodeAndEdge(
        countyName,
        smallTag,
        startTime,
        endTime,
        productList,
        storesToQuery,
        district, #narrow down
        segment,
        limit
    )

    if pictureType == BUY_WITH:
        options = set(df['ELEMENT1']).union(set(df['ELEMENT2']))
        print(countyName)
        return render(
            request, 'Display.html', {
                'startTime': startTime,
                'endTime': endTime,
                'districtList': districtList,
                'selectedPath': request.session.get('selectedPath', ''),
                'displayType': displayType,
                'stores': storeCanBeChoose,
                'relationship': relationship,
                'articulationPoint': articulationPoint,
                'communities': communities,
                'options': options,
                'nodes': nodes,
                'edges': edges,
                'countyName': countyName,
                'smallTag': smallTag,
                'productList': productList,
                'limit': limit,
                "districtName": district,
                'path': storesToQuery
            }
        )
    elif pictureType in (RFM, RFM_WITH_PRODUCT):
        return render(
            request, 'DisplayRFM.html', {
                'startTime': startTime,
                'endTime': endTime,
                'districtList': districtList,
                'selectedPath': request.session.get('selectedPath', ''),
                'displayType': displayType,
                'stores': storeCanBeChoose,
                'relationship': relationship,
                'articulationPoint': articulationPoint,
                'communities': communities,
            }
        )


def _drawPic(
    countyName,
    smallTag,
    pictureType,
    startTime=None,
    endTime=None,
    productList=None,
    storeTypeList=None,
    districtName=None,
    segment=None,
    limit=None
):
    if pictureType == PRODUCT_IN_PATH:
        network = ProductNetwork(username='admin', network_name='通路')
        if productList:

            df = network.get_channel_with_item_name(productList)
        else:
            df = network.get_channel_with_item_tag(smallTag)
        return df
    else:
        if not limit:
            #limit default value
            limit = 100
        network = ProductNetwork(username='admin', network_name='啤酒網路圖')
        df = network.query(
            county=countyName,
            city_area=districtName,
            item_tag=smallTag,
            datetime_lower_bound=startTime,
            datetime_upper_bound=endTime,
            store_brand_name=storeTypeList,
            item_name=productList,
            segment=segment,
            limit=limit
        )
        # network.execute_query()
        # network.analysis(limits=100)
        network.create_network()
        relationship, articulationPoint, communities = network.vis_all_graph()
        return relationship, articulationPoint, communities, df


def _getNodeAndEdge(
    countyName,
    smallTag,
    startTime=None,
    endTime=None,
    productList=None,
    storeTypeList=None,
    districtName=None,
    segment=None,
    limit=None
):

    if not limit:
        #limit default value
        limit = 100
    network = ProductNetwork(username='admin', network_name='啤酒網路圖')
    df = network.query(
        county=countyName,
        city_area=districtName,
        item_tag=smallTag,
        datetime_lower_bound=startTime,
        datetime_upper_bound=endTime,
        store_brand_name=storeTypeList,
        item_name=productList,
        segment=segment,
        limit=limit
    )
    # network.execute_query()
    # network.analysis(limits=100)
    network.create_network()
    network.vis_all_graph()
    nodes = network.get_nodes()
    edges = network.get_edges()
    return nodes, edges


def drawBuyWith(request):
    displayType = request.GET.get('displayType', 'Regular')
    step = request.GET.get('step', 'select_area')
    pictureType = BUY_WITH
    if step == 'select_area':
        request.session.clear()
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
    elif displayType == "Community":
        content = "Information about Community."
    else:
        content = "Information about Regular."

    return JsonResponse({"content": content})


##防呆
##資料篩選
def drawPath(request):
    step = request.GET.get('step', 'select_area')
    pictureType = PRODUCT_IN_PATH
    if step == 'select_area':
        request.session.clear()
        response = _selectArea(request, pictureType)

    elif step == 'select_time':
        response = _selectPathAndTime(request, pictureType)

    elif step == 'select_tag':
        response = _selectTag(request, pictureType)

    elif step == 'display_picture':
        response = _displayPathPic(request)

    else:
        response = redirect('/draw_product_in_path/?step=select_area')

    if response is None:
        print(f"drawPath returned None for step: {step}")
        return HttpResponse("An error occurred: No valid response was generated.", status=500)

    return response


def analyze(request):
    if request.method == 'POST':
        nodes = request.POST.get('nodes', '')
        edges = request.POST.get('edges', '')

        if not nodes or not edges:
            return render(request, 'Analysis.html', {'error': 'Nodes or edges data is missing'})
        print('Nodes:', nodes)
        print('Edges:', edges)

        chatbot = Chatbot()
        result = chatbot.generate_category_analysis(nodes, edges)

        return render(request, 'Analysis.html', {'analysis_result': result})

    return render(request, 'Analysis.html', {'error': 'Invalid request method'})


def displayOvertime(request):
    return render(request, 'Overtime.html')


def getDeeperInsight(request):
    option = request.GET.get('option')
    startTime = request.session.get('startTime', '')
    endTime = request.session.get('endTime', '')
    countyName = request.session.get('selectedCounty', '')
    storeTypeList = request.session.get('storeTypeList', '')
    district = request.session.get('selectedDistrict', '')
    limit = request.session.get('limit', '100')

    if not option:
        return redirect('/draw_buy_with/?step=display_picture')
    network = ProductNetwork(username='admin', network_name='啤酒網路圖')
    table = network.get_item_name(
        item_tag=option,
        datetime_lower_bound=startTime,
        datetime_upper_bound=endTime,
        store_brand_name=storeTypeList,
        county=countyName,
        city_area=district,
        limit=limit
    )
    table = network.get_item_name(option)
    context = {'table': table}
    return render(request, 'DeeperInsight.html', context)


def drawRFM(request):
    step = request.GET.get('step', 'select_area')
    pictureType = RFM

    displayType = request.GET.get('displayType', 'Regular')
    if step == 'select_area':
        request.session.clear()
        return _selectArea(request, pictureType)

    elif step == 'select_path_time':
        return _selectPathAndTime(request, pictureType)

    elif step == 'display_picture':
        return _displayPic(request, pictureType, displayType)

    return redirect('/draw_buy_with/?step=select_area')


def drawRFMwithProduct(request):
    step = request.GET.get('step', 'select_area')
    pictureType = RFM_WITH_PRODUCT

    displayType = request.GET.get('displayType', 'Regular')
    if step == 'select_area':
        return _selectArea(request, pictureType)

    elif step == 'select_path_time':
        return _selectPathAndTime(request, pictureType)

    elif step == 'select_tag':
        return _selectTag(request, pictureType)

    elif step == 'display_picture':
        return _displayPic(request, pictureType, displayType)

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


def displayBuyWithInPath(request):
    startTime = request.session.get('startTime', '')
    endTime = request.session.get('endTime', '')
    countyName = request.session.get('selectedCounty', '')
    #district = request.session.get('selectedDistrict', '') # narrow down 才有
    smallTag = request.session.get('smallTag', '')
    productList = request.session.get('productList', '')
    store = request.GET.get('store')

    network = ProductNetwork(username='admin', network_name='啤酒網路圖')
    df = network.query(
        county=countyName,
        item_tag=smallTag,
        datetime_lower_bound=startTime,
        datetime_upper_bound=endTime,
        store_brand_name=store,
        item_name=productList,
        limit=100
    )
    # network.execute_query()
    # network.analysis(limits=100)
    network.create_network()
    relationship, articulationPoint, communities = network.vis_all_graph()
    return render(
        request, 'BuyWithInPath.html', {
            'relationship': relationship,
            'articulationPoint': articulationPoint,
            'communities': communities,
        }
    )
