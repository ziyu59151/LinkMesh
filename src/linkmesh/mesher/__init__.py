"""
mesher —— TokaMaker/Triangle 唯一网格生成底座子包。

公开接口：
    generate_mesh(config: BoundaryConfig) -> Mesh2D

重要约束：
    - 本子包是 LinkMesh 唯一的网格生成引擎，严禁引入第二种生成引擎
    - 严禁引入三维网格生成逻辑
"""
