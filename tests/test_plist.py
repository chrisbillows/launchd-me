import pytest

import launchd_me

@pytest.fixture
def plc():
    plc = launchd_me.PlistCreator()
    return plc

def test_plist_creator_init(plc, tmp_path):
    pass
    
    
    