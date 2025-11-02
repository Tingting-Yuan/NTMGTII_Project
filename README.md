# Dijkstra Shortest Path Algorithm

## Project Overview

This project provides a complete Python implementation of **Dijkstra’s algorithm** for finding the shortest path in a weighted graph. The implementation is encapsulated in `dijkstra.py` and supports:

- Adding vertices and their edges with weights.
- Computing the shortest path between two nodes.
- Handling cases where nodes are not in the graph or are disconnected.
- Returning the **full path** as a list of nodes.

This implementation is suitable for educational purposes, demonstrations, or as a foundation for larger graph/network projects.

---

## Features

- **Dynamic graph creation**: Add any number of vertices and edges.  
- **Shortest path calculation**: Computes forward paths using Dijkstra’s algorithm.  
- **Edge cases handled**:  
  - Path to self (`A → A`)  
  - Nonexistent nodes return `None`  
  - Disconnected nodes return `None`  
- **Readable output**: Returns the shortest path as a list of node names.

---

## Files

| File | Description |
|------|-------------|
| `dijkstra.py` | Main implementation of Dijkstra’s algorithm with `Graph` class. |
| `test.py` | Unit tests for multiple graphs and edge cases using `unittest`. (Don't change.)|

---

## Usage

```python
from dijkstras import Graph

# Create a graph
g = Graph()
g.add_vertex('A', {'B': 7, 'C': 8})
g.add_vertex('B', {'A': 7, 'F': 2})
g.add_vertex('C', {'A': 8, 'F': 6, 'G': 4})
g.add_vertex('F', {'B': 2, 'C': 6})
g.add_vertex('G', {'C': 4})

# Compute shortest path
path = g.shortest_path('A', 'G')
print(path)  # Output: ['A', 'C', 'G']
