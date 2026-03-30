import os
from pathlib import Path
cwd = os.getcwd()

relative_path = "../../../"

print(f"os当前工作目录: {cwd}")
print(f"path当前工作目录: {Path.cwd()}")
print('---')
path_cwd = Path(relative_path)
print(f"path_cwd.resolve(): {path_cwd.resolve()}")