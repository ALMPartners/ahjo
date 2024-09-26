# Ahjo - Database deployment framework
#
# Copyright 2019 - 2024 ALM Partners Oy
# SPDX-License-Identifier: Apache-2.0

""" Module for visualization operations. """
import networkx as nx
from logging import getLogger

try:
    import plotly.graph_objects as go
except:
    go = None

logger = getLogger('ahjo')

def plot_dependency_graph(G, layout: str = "spring_layout"):
    """Plot a dependency graph with Plotly.

    Parameters
    ----------
    G : networkx.DiGraph
        A directed graph representing dependencies between objects.
    """
    try:
        if layout == "spring_layout":
            pos = nx.spring_layout(G)
        elif layout == "kamada_kawai_layout":
            pos = nx.kamada_kawai_layout(G)
        elif layout == "planar_layout":
            pos = nx.planar_layout(G)
        elif layout == "shell_layout":
            pos = nx.shell_layout(G)
        elif layout == "spectral_layout":
            pos = nx.spectral_layout(G)
        elif layout == "circular_layout":
            pos = nx.circular_layout(G)
        elif layout == "random_layout":
            pos = nx.random_layout(G)
        else:
            pos = nx.spring_layout(G)

        edge_x = []
        edge_y = []
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            edge_x.append(x0)
            edge_x.append(x1)
            edge_x.append(None)
            edge_y.append(y0)
            edge_y.append(y1)
            edge_y.append(None)

        node_x = []
        node_y = []
        node_color = []
        node_size = []
        for node in G.nodes():
            x, y = pos[node]
            node_x.append(x)
            node_y.append(y)
            node_color.append(G.nodes[node].get("created_object_type", "default"))
            node_size.append(15 + (G.in_degree(node)))

        fig = go.Figure()
        fig.add_trace(
            go.Scatter(
                x=edge_x, y=edge_y, 
                mode="lines",
                line=dict(width=0.1, color="black"), 
                hoverinfo = "none", 
                showlegend = False, 
                line_shape = "linear"
            )
        )
        fig.add_trace(
            go.Scatter(
                x=node_x, 
                y=node_y, 
                mode="markers",
                text = list(G.nodes()), 
                hoverinfo = "text", 
                textposition = "top center",
                marker = dict(
                    color = [list(set(node_color)).index(x) for x in node_color], 
                    size = node_size,
                    line=dict(width=2, color='black')
                )
            )
        )
        
        for edge in G.edges():
            x0, y0 = pos[edge[0]]
            x1, y1 = pos[edge[1]]
            fig.add_annotation(
                x=x1, y=y1,
                ax=x0, ay=y0,
                xref="x", yref="y",
                axref="x", ayref="y",
                showarrow=True,
                arrowhead=5,
                arrowsize=2,
                arrowcolor="black"
            )

        fig.update_layout(
            title="Dependency Graph", 
            showlegend=False, 
            hovermode="closest",
            xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
            yaxis=dict(showgrid=False, zeroline=False, showticklabels=False)
        )

        fig.show()

    except Exception as e:
        logger.error(f"Error plotting dependency graph: {e}")