import numpy as np
from secquery.index import VectorIndex


def test_index_incremental_add_search_and_persistence(tmp_path):
    path = tmp_path / "faiss.index"
    index = VectorIndex(3, path)
    index.add(["a"], np.array([[1, 0, 0]], dtype=np.float32))
    index.add(["b"], np.array([[0, 1, 0]], dtype=np.float32))
    index.add(["a"], np.array([[0, 0, 1]], dtype=np.float32))  
    assert [item[0] for item in index.search(np.array([[1, 0, 0]]), 2)][0] == "a"
    index.save()
    loaded = VectorIndex(3, path)
    assert loaded.load()
    assert set(loaded.chunk_ids) == {"a", "b"}
