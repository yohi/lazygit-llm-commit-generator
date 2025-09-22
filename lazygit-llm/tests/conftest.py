"""
テスト設定とフィクスチャ
"""

import pytest
import sys
from pathlib import Path

# プロジェクトのルートディレクトリをPythonパスに追加
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

@pytest.fixture(autouse=True)
def setup_logging():
    """テスト用のログ設定"""
    import logging
    logging.basicConfig(level=logging.DEBUG)
    
@pytest.fixture
def sample_messages():
    """テスト用のサンプルメッセージ"""
    return {
        'short': 'fix: bug',
        'normal': 'feat: add user authentication',
        'long': 'feat: implement comprehensive user authentication system with JWT tokens and password hashing',
        'with_code': '''```python
def test():
    pass
```
Add test function''',
        'with_quotes': '"Add new feature"',
        'with_prefix': 'Commit message: fix bug in parser',
        'empty': '',
        'whitespace': '   \n\t  ',
        'multiline': '''First line of commit
        
This is the body of the commit
with multiple lines and details.''',
    }