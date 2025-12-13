import sys
import os
import pytest
sys.path.append(os.path.dirname(__file__))

from complex_flow import create_server_troubleshooting_flow

@pytest.fixture
def complex_flowchart():
    return create_server_troubleshooting_flow()
