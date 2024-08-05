import networkx as nx
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pyvis.network import Network
import datetime
import os
import psycopg2


class ProductNetwork:
    #flow: initialize network -> setQuery -> executeQuery -> analysis -> create network ->visualize
    """
    Initialization
    self.query_network: the query statements

    self.graph: <networkx graph>
    self.original_graph: path of original graph
    self.articultion_graph: path of graph with articulation points
    self.community_graph: path of graph with community 

    """

    def __init__(self, username, network_name, type=None, tag=None):

        self.username = username
        self.network_name = network_name

        if not os.path.exists(f'./{username}/{network_name}'):
            os.makedirs(f'./{username}/{network_name}')

        self.query_network = None
        self.type = type #Category, Product, RFM
        self.tag = tag #put specific category here

        self.graph = None
        self.node_attributes = None
        self.edge_attributes = None

        self.original_graph = None
        self.articulation_graph = None
        self.community_graph = None

        self.communities = None
        self.articulation_points = None
        self.relationship_df = None
        self.channel_df = None

        self.query_list = None
        self.condition = None

        #to do save
        self.directory = None

        conn = psycopg2.connect(
            database="InvoicePlatform", user="postgres", password="0000", host="127.0.0.1", port="5432"
        )
        self.cur = conn.cursor()

    def query(
        self,
        query=None,
        datetime_lower_bound=None,
        datetime_upper_bound=None,
        item_name=None,
        unit_price_lower_bound=None,
        unit_price_upper_bound=None,
        item_tag=None,
        item_brand_name=None,
        store_brand_name=None,
        county=None,
        city_area=None,
        segment=None
    ):
        condition = ''
        if datetime_lower_bound:
            condition += f"AND datetime >= '{datetime_lower_bound}' "
        if datetime_upper_bound:
            condition += f"AND datetime <= '{datetime_upper_bound}'"
        if item_name:
            condition += f"AND item_name = '{item_name}'"
        if unit_price_lower_bound:
            condition += f"AND unit_price >= '{unit_price_lower_bound}'"
        if unit_price_upper_bound:
            condition += f"AND unit_price <= '{unit_price_upper_bound}'"

        if item_brand_name:
            condition += f"AND item_brand_name = '{item_brand_name}'"
        if store_brand_name:
            condition += f"AND store_brand_name = '{store_brand_name}'"
        if county:
            condition += f"AND county = '{county}'"
        if city_area:
            condition += f"AND city_area = '{city_area}'"
        if segment:
            condition += f"AND segment = '{segment}'"

        if item_tag:
            self.type = item_tag
            condition += f"AND test.inv_num in (SELECT inv_num FROM test WHERE test.item_tag = '{item_tag}') "

        if not query:
            query = 'SELECT * FROM test WHERE 1=1 ' + condition
        else:
            query = query + condition
        print(query)
        self.condition = condition
        self.cur.execute(f"CREATE OR REPLACE VIEW search_temp AS ({query})")
        #self.cur.execute(f"SELECT * INTO search_temp_id FROM test WHERE 1=1 "+condition)

    def execute_query(self):
        self.cur.execute(
            """
                SELECT a.item_tag as Element1, b.item_tag as Element2, a.inv_num, a.datetime, a.store_brand_name, a.item_brand_name, a.segment
                INTO TEMPORARY results
                FROM search_temp a
                JOIN search_temp b
                ON a.inv_num = b.inv_num
                WHERE a.item_tag < b.item_tag
                """
        )
        return

    def create_network(self):
        links = self.relationship_df
        g = nx.from_pandas_edgelist(links, 'ELEMENT1', 'ELEMENT2', edge_attr=True, create_using=nx.Graph())

        # Add item_tag as node attribute
        for node in g.nodes():
            item_tags = links.loc[(links['ELEMENT1'] == node) | (links['ELEMENT2'] == node), 'item_tag']
            if not item_tags.empty:
                g.nodes[node]['item_tag'] = item_tags.iloc[0]

        self.g = g
        return g

    def visualize_graph(self, g, _type):
        if g is None:
            print("Empty graph, nothing to visualize.")
            return None

        graph = Network(notebook=True)
        node_attributes = pd.DataFrame(g.degree, columns=['Node', 'Degree'])

        self.articulation_points = list(nx.articulation_points(g))
        a_tf = []
        for i in range(0, node_attributes.shape[0]):
            if node_attributes['Node'][i] in self.articulation_points:
                a_tf.append(True)

            else:
                a_tf.append(False)
        node_attributes['is_articulation_point'] = a_tf

        comm = nx.community.louvain_communities(g, seed=123)
        self.communities = comm
        community = {}
        for i in range(0, len(comm)):
            for item in comm[i]:
                community[item] = i
        color = [
            '#FF0000', '#00FFFF', '#FFA500', '#800080', '#A52A2A', '#FFFF00', '#800000', '#008000', '#FF00FF',
            '#808000', '#FFC0CB', '#7FFFD4'
        ]
        node_attributes['Group'] = [community[node_attributes['Node'][i]] for i in range(0, node_attributes.shape[0])]

        # Get the item_tag from node attributes
        item_tag = None

        for node in g.nodes(data=True):
            if 'item_tag' in node[1]:
                item_tag = node[1]['item_tag']
                break

        node_attributes['Size'] = np.sqrt(node_attributes['Degree']) * 5

        if _type == "original" or _type == None:
            node_attributes['Color'] = np.where(node_attributes['Node'] == item_tag, 'orange', 'orange')
        else:
            node_attributes['Color'] = np.where(node_attributes['Node'] == item_tag, 'red', 'orange')

        if _type == "articulation":

            for i in range(0, node_attributes.shape[0]):
                if node_attributes['Node'][i] in self.articulation_points:
                    node_attributes['Color'][i] = 'green'

                if node_attributes['Node'][i] == item_tag:
                    node_attributes['Color'][i] = 'red'

        if _type == "community":
            node_attributes['Color'] = [
                color[community[node_attributes['Node'][i]]] for i in range(0, node_attributes.shape[0])
            ]

        node_attributes['Title'] = node_attributes.apply(lambda x: f"{x['Node']}\nDegree: {x['Degree']}", axis=1)

        print(node_attributes)

        for _, row in node_attributes.iterrows():
            graph.add_node(row['Node'], size=row['Size'], color=row['Color'], title=row['Title'])

        edge_attributes = pd.DataFrame(g.edges(data=True), columns=['Source', 'Target', 'COUNTS'])
        for _, row in edge_attributes.iterrows():
            weight_title = f"Weight: {row['COUNTS']['COUNTS']}"
            graph.add_edge(
                row['Source'], row['Target'], color='silver', title=weight_title, width=(row['COUNTS']['COUNTS'] / 300)
            )

        print(node_attributes)
        print(edge_attributes)
        self.node_attributes = node_attributes
        self.edge_attributes = edge_attributes
        html_content = graph.generate_html(notebook=False)

        return html_content

    def analysis(self, limits=100):
        self.cur.execute("SELECT element1, element2, count(datetime) as c FROM results GROUP BY element1, element2")
        df = pd.DataFrame(self.cur.fetchall())
        print(df)

        if df.shape[0] == 0:
            print('The result of this query contains no data')
            return None

        if limits > df.shape[0]:
            limits = df.shape[0]

        df = df.sort_values([2], ascending=False)
        df[3] = df[2] / (df[2].sum()) * 100
        df = df.rename(columns={0: 'ELEMENT1', 1: 'ELEMENT2', 2: 'COUNTS', 3: 'PERCENTAGE'})
        df = df[:limits].round({3: 2}).reset_index(drop=True)
        print(df)

        if self.type == 'Category':
            df['item_tag'] = [self.type for i in range(0, df.shape[0])]
        else:
            df['item_tag'] = ['' for i in range(0, df.shape[0])]

        #if df.shape[0] > 100:
        #    df = df.iloc[:100,:]
        #da = df
        df.reset_index(drop=True)
        self.relationship_df = df
        return df

    def vis_all_graph(self):
        return [self.vis_original_graph(), self.vis_articulation_graph(), self.vis_community_graph()]

    def vis_original_graph(self):
        original_graph_name = 'origin_case.html'
        graph_html = self.visualize_graph(self.g, _type='original')
        self.original_graph = original_graph_name
        return graph_html

    def vis_articulation_graph(self):
        articulation_graph_name = 'articulation_case.html'
        graph_html = self.visualize_graph(self.g, _type='articulation')
        self.articulation_graph = articulation_graph_name
        return graph_html

    def vis_community_graph(self):
        community_graph_name = 'community_case.html'
        graph_html = self.visualize_graph(self.g, _type='community')
        self.community_graph = community_graph_name
        return graph_html

    def get_articulation_points(self):
        return self.articulation_points

    def get_communities(self):
        return self.communities

    def get_relationship_df(self):
        return self.relationship_df

    def get_nodes(self):
        return self.node_attributes

    def get_edges(self):
        return self.edge_attributes
