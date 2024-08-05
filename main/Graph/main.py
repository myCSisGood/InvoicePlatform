import networks
import psycopg2
import chatbot

if __name__ == '__main__':

    network = networks.ProductNetwork(username='admin', network_name='啤酒網路圖')
    network.query(county='臺北市', item_tag='啤酒')
    network.execute_query()
    network.analysis(limits=100)
    network.create_network()
    a, b, c = network.vis_all_graph()
    print(network.get_relationship_df())
    print(network.get_articulation_points())
    print(network.get_communities())

    chatgpt = chatbot.Chatbot()
    analysis = chatgpt.generate_category_analysis(network.get_nodes(), network.get_edges())
    print(analysis)

    quotes = chatgpt.generate_slogan(network.get_nodes(), network.get_edges())
    print(quotes)

    network = networks.ProductNetwork(username='betty', network_name='台北中山冰品冬天')
    network.query(
        county='臺北市',
        city_area='中山區',
        item_tag='冰淇淋/冰棒/剉冰',
        datatime_lower_bound='2020-11-01',
        datatime_upper_bound='2020-12-31',
        store_brand_name='統一超商_7Eleven'
    )
    network.execute_query()
    network.analysis(limits=100)
    network.create_network()
    path_list = network.vis_all_graph()
    print(path_list)
    print(network.get_relationship_df())
    print(network.get_articulation_points())
    print(network.get_communities())

    chatgpt = chatbot.Chatbot()
    analysis = chatgpt.generate_category_analysis(network.get_nodes(), network.get_edges())
    print(analysis)

    quotes = chatgpt.generate_slogan(network.get_nodes(), network.get_edges())
    print(quotes)

    network = networks.ProductNetwork(username='betty', network_name='台北中山冰品夏天')
    network.query(
        county='臺北市',
        city_area='中山區',
        item_tag='冰淇淋/冰棒/剉冰',
        datatime_lower_bound='2020-07-01',
        datatime_upper_bound='2020-08-31',
        store_brand_name='統一超商_7Eleven'
    )
    network.execute_query()
    network.analysis(limits=100)
    network.create_network()
    path_list = network.vis_all_graph()
    print(path_list)
    print(network.get_relationship_df())
    print(network.get_articulation_points())
    print(network.get_communities())

    chatgpt = chatbot.Chatbot()
    analysis = chatgpt.generate_category_analysis(network.get_nodes(), network.get_edges())
    print(analysis)

    quotes = chatgpt.generate_slogan(network.get_nodes(), network.get_edges())
    print(quotes)

    #print(result)

    #conn = psycopg2.connect(database="postgres",
    #                    user = "postgres",
    #                    password = "0000",
    #                    host="127.0.0.1",
    ##                    port="5432")
    #cur = conn.cursor()
    #network = networks.ProductNetwork(cur)
    ##network.query(county='新北市', city_area='永和區', item_tag='健身')
    ##result = network.execute()
    #print(result)
