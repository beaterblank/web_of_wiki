import os
import pickle
from collections import deque
import requests
from bs4 import BeautifulSoup
from urllib.parse import quote, unquote
import time
import json
import streamlit as st
import networkx as nx
import plotly.graph_objects as go

def get_url(url):
    return requests.get(url)

def get_adj(item):
    domain = 'https://en.wikipedia.org/wiki/'
    url = domain + quote(item)
    # send a GET request to the website
    response = requests.get(url)
    # create a BeautifulSoup object to parse the HTML content
    soup = BeautifulSoup(response.content, "html.parser")
    # find the element with the ID "content"
    content = soup.find("main", {"id": "content"})
    # find all links within the "content" element
    links = content.find_all("a")
    # iterate through the links and print those with URLs starting with "https://en.wikipedia.org/wiki/"
    filters = ["Wikipedia", "Category", "File", "Help", "Special", "identifier", "%","Template","#","Wayback_Machine","Portal"]
    out = set()
    for link in links:
        href = link.get("href")
        if href and str(href).startswith("/wiki/") and not any([item in href for item in filters]):
            out.add(unquote(str(href).replace("/wiki/", "")))
    return out




def crawl(start, max_pages, state_file=None,save=False,pbar=None):
    state_file = f"{start}/state_{max_pages}.pkl"
    adjs = dict()
    visited = set()
    q =  deque()
    q.append(start)
    visited.add(start)

    if state_file and os.path.isfile(state_file) and save:
        with open(state_file, 'rb') as f:
            adjs,visited,q = pickle.load(f)

    start_time = time.time()
    while q and len(visited) < max_pages:
        item = q.popleft()
        links = adjs.get(item)
        if links is None:
            links = get_adj(item)
            adjs[item] = list(links)
        for link in links:
            if link not in visited:
                visited.add(link)
                q.append(link)
        if(pbar):
            pbar.progress(min(len(visited) / max_pages,1.0))
        if state_file and time.time() - start_time > 300 and save:
            with open(state_file, 'wb') as f:
                pickle.dump((adjs, visited,q), f)
            start_time = time.time()
    if save:
        with open(state_file, 'wb') as f:
            pickle.dump((adjs, visited,q), f)
    return adjs

def is_valid(input_text):
    url = 'https://en.wikipedia.org/wiki/' + input_text
    response = requests.get(url)
    return response.status_code == 200 and input_text!=''

def ranker(adjacency_list):
    node_counts = {}
    for node, neighbors in adjacency_list.items():
        if node not in node_counts:
            node_counts[node] = 0
        for neighbor in neighbors:
            if neighbor not in node_counts:
                node_counts[neighbor] = 1
            else:
                node_counts[neighbor] += 1
    pairs = sorted(node_counts.items(), key=lambda item: item[1], reverse=True)
    node_counts_sorted = dict(pairs[:min(100,len(pairs))])
    node_count = node_counts_sorted
    adj_list = {k: [it for it in v if it in node_count] for k, v in adjacency_list.items() if k in node_count}
    if(len(adj_list)==0):
        st.write("nothing interconnects here")
    G = nx.DiGraph()
    # Add nodes from the adjacency list
    G.add_nodes_from(adj_list.keys())

    # Add edges from the adjacency list
    for node, neighbors in adj_list.items():
        for neighbor in neighbors:
            G.add_edge(node, neighbor)
    pos = nx.arf_layout(G) 
    edge_x = []
    edge_y = []
    for edge in G.edges():
        x0, y0 =pos[edge[0]]
        x1, y1 = pos[edge[1]]
        edge_x.append(x0)
        edge_x.append(x1)
        edge_x.append(None)
        edge_y.append(y0)
        edge_y.append(y1)
        edge_y.append(None)

    edge_trace = go.Scatter(
        x=edge_x, y=edge_y,
        line=dict(width=0.5, color='#888'),
        hoverinfo='none',
        mode='lines')

    node_x = []
    node_y = []
    for node in G.nodes():
        x, y = pos[node]
        node_x.append(x)
        node_y.append(y)

    node_trace = go.Scatter(
        x=node_x, y=node_y,
        mode='markers',
        hoverinfo='text',
        marker=dict(
            showscale=True,
            colorscale='YlGnBu',
            reversescale=True,
            color=[],
            size=10,
            colorbar=dict(
                thickness=15,
                title='Node Connections',
                xanchor='left',
                titleside='right'
            ),
            line_width=2))
    node_adjacencies = []
    node_text = []
    for node in G.nodes():
        node_adjacencies.append(node_count[node] if node in node_count else 0)
        node_text.append(str(node)+" : "+str(node_count[node] if node in node_count else 0))

    node_trace.marker.color = node_adjacencies
    node_trace.text = node_text
    fig = go.Figure(data=[edge_trace, node_trace],
            layout=go.Layout(
            title='',
            titlefont_size=16,
            showlegend=False,
            hovermode='closest',
            margin=dict(b=20,l=5,r=5,t=40),
            annotations=[ dict(
                text = "",
                showarrow=False,
                xref="paper", yref="paper",
                x=0.005, y=-0.002 ) ],
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False))
            )
    return fig,node_counts

if __name__ == '__main__':
    st.title("Web of Wiki")
    st.write("This is a wikipedia links crawler, goto any wikipedia article u wish and copy the last part of url to see what links are interconnected with it the most ")
    #c1,c2 = st.columns(2)
    #save_state = c1.checkbox(label="save states?(recomended for huge crawling)",value=True)
    #fresh_run = c2.checkbox(label="fresh run?(deleted saved state for the input)")
    hide_st_style = """
            <style>
            #MainMenu {visibility: hidden;}
            footer {visibility: hidden;}
            header {visibility: hidden;}
            </style>
            """
    st.markdown(hide_st_style, unsafe_allow_html=True)
    st.markdown("""
        <style>
               .block-container {
                    padding-top: 1rem;
                    padding-bottom: 0rem;
                    padding-left: 5rem;
                    padding-right: 5rem;
                }
        </style>
        """, unsafe_allow_html=True)
    save_state=False
    fresh_run=False
    c1,c2 = st.columns([3,1])
    start = c1.text_input(label="Enter a wikipedia article",value="India")
    if(fresh_run and os.path.isfile(start)):
        os.remove(start)
    max_pages = int(c2.number_input(label="Enter max links to crawled",value=10000,step=5000))
    if(is_valid(start) and max_pages>999):
        if not os.path.exists(start) and save_state:
            os.makedirs(start)
        pbar = st.progress(0.0)
        adjacency_list = crawl(start=start, max_pages = max_pages,save=save_state,pbar=pbar)

        pbar.empty()
        if save_state:
            with open(f"{start}/adj.json", "w", encoding="utf-8") as f:
                json.dump(adjacency_list, f, ensure_ascii=False)
        fig,node_count = ranker(adjacency_list=adjacency_list)
        st.plotly_chart(fig,use_container_width=True)
        
        if save_state:
            with open(f"{start}/ranks.json", "w", encoding="utf-8") as f:
                json.dump(node_count, f, ensure_ascii=False)
        
    else:
        st.write("Please enter a valid Wiki Page and more than 1000 max pages")
