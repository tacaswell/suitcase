from metadatastore.test.utils import mds_setup, mds_teardown
from metadatastore.examples.sample_data import temperature_ramp
from databroker import db, get_table
from suitcase import hdf5
import tempfile
import h5py
import numpy as np
import pytest


def setup_function(function):
    mds_setup()


def teardown_function(function):
    mds_teardown()


def shallow_header_verify(hdf_path, header, fields=None):
    table = get_table(header)
    with h5py.File(hdf_path) as f:
        # make sure that the header is actually in the file that we think it is
        # supposed to be in
        assert header.start.uid in f
        assert dict(header.start) == eval(f[header.start.uid].attrs['start'])
        assert dict(header.stop) == eval(f[header.start.uid].attrs['stop'])
        # make sure the descriptors are all in the hdf output file
        for descriptor in header.descriptors:
            descriptor_path = '%s/%s' % (header.start.uid, descriptor.uid)
            assert descriptor_path in f
            # make sure all keys are in each descriptor
            for key in descriptor.data_keys:
                data_path = "%s/data/%s" % (descriptor_path, key)
                # check the case when fields kwd is used
                if fields is not None:
                    if key not in fields:
                        assert data_path not in f
                        continue
                # make sure that the data path is in the file
                assert data_path in f
                # make sure the data is equivalent to what comes out of the
                # databroker
                hdf_data = np.asarray(f[data_path])
                broker_data = table[key].dropna().values
                assert all(hdf_data == broker_data)
                # make sure the data is sorted in chronological order
                timestamps_path = "%s/timestamps/%s" % (descriptor_path, key)
                timestamps = np.asarray(f[timestamps_path])
                assert all(np.diff(timestamps) > 0)


def test_hdf5_export_single():
    """
    Test the hdf5 export with a single header and
    verify the output is correct
    """
    temperature_ramp.run()
    hdr = db[-1]
    fname = tempfile.NamedTemporaryFile()
    hdf5.export(hdr, fname.name)
    shallow_header_verify(fname.name, hdr)


@pytest.mark.xfail(reason='name is not included as a key at descriptor'
                          'from data created at temperature_ramp.'
                          'But descriptor name is used for real experiment.')
def test_hdf5_export_single_no_uid():
    """
    Test the hdf5 export with a single header and
    verify the output is correct. No uid is used.
    """
    temperature_ramp.run()
    hdr = db[-1]
    fname = tempfile.NamedTemporaryFile()
    hdf5.export(hdr, fname.name, use_uid=False)
    shallow_header_verify(fname.name, hdr)


def test_hdf5_export_with_fields_single():
    """
    Test the hdf5 export with a single header and
    verify the output is correct; fields kwd is used.
    """
    temperature_ramp.run()
    hdr = db[-1]
    fname = tempfile.NamedTemporaryFile()
    hdf5.export(hdr, fname.name, fields=['point_dev'])
    shallow_header_verify(fname.name, hdr, fields=['point_dev'])


def test_filter_fields():
    temperature_ramp.run()
    hdr = db[-1]
    unwanted_fields = ['point_det']
    out = hdf5.filter_fields(hdr, unwanted_fields)
    assert len(out)==1  #original list is ('point_det', 'Tsam'), only ('Tsam') left after filtering out


def test_hdf5_export_list():
    """
    Test the hdf5 export with a list of headers and
    verify the output is correct
    """
    temperature_ramp.run()
    temperature_ramp.run()
    hdrs = db[-2:]
    fname = tempfile.NamedTemporaryFile()
    # test exporting a list of headers
    hdf5.export(hdrs, fname.name)
    for hdr in hdrs:
        shallow_header_verify(fname.name, hdr)
