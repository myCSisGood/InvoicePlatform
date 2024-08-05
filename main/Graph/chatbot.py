import networkx as nx
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from pyvis.network import Network
from langchain_community.chat_models import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain.schema import (HumanMessage)
import os


class Chatbot:

    def __init__(self):
        self.type = type
        os.environ["OPENAI_API_KEY"] = 'sk-proj-TWYkldfGdBsKtUH447xRT3BlbkFJSqrqTJj1alzcWZz4GpQm'

        #type: quote, category, product, rfm, comparison...

    def generate_text(self, nodes, edges, item_tag, type):
        pass

    def generate_slogan(self, node, edge):
        node = node.to_string()
        edge = edge.to_string()
        content = f"""你現在是一位專業的市場行銷專家。
                  以下將提供該graph的node(node_name, degree, color, group, is_articulation_point)和edge(from, to, counts)
                  Node為：{node}，Edge為：{edge}，
                  請選擇適合的倂買關係來生成3個以上的行銷文案，文案必須幽默有趣。
                  """
        chat = ChatOpenAI(model_name="gpt-4o", temperature=0)
        resp = chat([HumanMessage(content=content)])
        answer = resp.content
        return answer

    def generate_category_analysis(self, node, edge):
        node = node.to_string()
        edge = edge.to_string()
        content = f"""你現在是一位專業的商業分析師，請提供一份超過3000字且完整且專業的產品銷售分析文字報告！！！。
                  以下將提供該graph的node(node_name, degree, color, group, is_articulation_point)和edge(from, to, counts)
                  Node為：{node}，Edge為：{edge}，
                  請依照以下步驟做詳細解釋，
                  1. 除了self-connected node之外，請找出倂買關係中，最好的前25%的倂買關係，並依比例大小做排序，列出他們的倂買次數（兩個類別產品都要列出）與比例。
                  2. 根據倂買關係的結果給予商家營業建議。
                  3. 每個node都有一個group屬性，代表該node所屬的community，請針對community做分析。
                  4. 每個node都有一個is_articulation_point屬性，代表該node是否為articulation_point，請針對articulation_point做分析。
                  5. 除了articulation_points相關的併買關係之外，請找出其他需要被促銷的產品關係。
                  請提供一份1超過3000字的完整網路圖分析報告，內容需清楚明瞭
                  """
        #5. 以下是過去一年前10名產品的eigenvector centrality，{ce}，請針對每項產品這一年的centrality變化趨勢做解釋。
        chat = ChatOpenAI(model_name="gpt-4o", temperature=0)
        resp = chat([HumanMessage(content=content)])
        answer = resp.content
        return answer
