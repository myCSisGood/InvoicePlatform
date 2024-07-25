import networkx as nx
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pyvis.network import Network
import datetime


class ProductNetwork:

    def __init__(self, cur):
        self.cur = cur
        self.query_network = None
        self.query_list = None
        self.condition = None

    def query(
        self,
        query=None,
        datatime_lower_bound=None,
        datatime_upper_bound=None,
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
        if datatime_lower_bound:
            condition += f"AND datatime >= '{datatime_lower_bound}' "
        if datatime_upper_bound:
            condition += f"AND datatime <= '{datatime_upper_bound}'"
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
            condition += f"AND test.inv_num in (SELECT inv_num FROM test WHERE test.item_tag = '{item_tag}') "

        if not query:
            query = 'SELECT * FROM test WHERE 1=1 ' + condition
        else:
            query = query + condition
        print(query)
        self.condition = condition
        self.cur.execute(f"CREATE OR REPLACE VIEW search_temp AS ({query})")
        #self.cur.execute(f"SELECT * INTO search_temp_id FROM test WHERE 1=1 "+condition)

    def create_network(self, links):
        g = nx.from_pandas_edgelist(links, 'ELEMENT1', 'ELEMENT2', edge_attr=True, create_using=nx.Graph())

        # Add item_tag as node attribute
        for node in g.nodes():
            item_tags = links.loc[(links['ELEMENT1'] == node) | (links['ELEMENT2'] == node), 'item_tag']
            if not item_tags.empty:
                g.nodes[node]['item_tag'] = item_tags.iloc[0]

        return g

    def visualize_graph(self, g):
        if g is None:
            print("Empty graph, nothing to visualize.")
            return None

        graph = Network(notebook=True)
        node_attributes = pd.DataFrame(g.degree, columns=['Node', 'Degree'])

        # Get the item_tag from node attributes
        item_tag = None

        for node in g.nodes(data=True):
            if 'item_tag' in node[1]:
                item_tag = node[1]['item_tag']
                break

        node_attributes['Size'] = np.sqrt(node_attributes['Degree']) * 5
        node_attributes['Color'] = np.where(node_attributes['Node'] == item_tag, 'orange', 'orange')
        node_attributes['Title'] = node_attributes.apply(lambda x: f"{x['Node']}\nDegree: {x['Degree']}", axis=1)

        print(node_attributes)

        for _, row in node_attributes.iterrows():
            graph.add_node(row['Node'], size=row['Size'], color=row['Color'], title=row['Title'])
        edge_attributes = pd.DataFrame(g.edges(data=True), columns=['Source', 'Target', 'COUNTS'])

        for _, row in edge_attributes.iterrows():
            weight_title = f"Weight: {row['COUNTS']['COUNTS']}"
            graph.add_edge(row['Source'], row['Target'], color='slver', title=weight_title)

        print(node_attributes)
        print(edge_attributes)
        html_content = graph.generate_html(notebook=False)

        return html_content

    def execute(self):
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
        self.cur.execute("SELECT element1, element2, count(datetime) as c FROM results GROUP BY element1, element2")
        df = pd.DataFrame(self.cur.fetchall())
        print(df.shape)
        df = df.sort_values([2], ascending=False)
        df[3] = df[2] / (df[2].sum()) * 100
        df = df.rename(columns={0: 'ELEMENT1', 1: 'ELEMENT2', 2: 'COUNTS', 3: 'PERCENTAGE'})
        df[:20].round({3: 2}).reset_index(drop=True)
        print(df)
        df['item_tag'] = ['啤酒' for i in range(0, df.shape[0])]
        if df.shape[0] > 100:
            df = df.iloc[:100, :]
        da = df
        da.reset_index(drop=True)
        g = self.create_network(da)
        return self.visualize_graph(g)
