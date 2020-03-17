import pandas as pd
import pytest
import sqlalchemy.exc

from ert_shared.storage import Observation
from ert_shared.storage.rdb_api import RdbApi
from ert_shared.storage.blob_api import BlobApi

from tests.storage import db_session, engine, tables


def test_add_observation(db_session):
    observation_name = "test"
    key_indexes = [0, 3]
    data_indexes = [0, 3]
    values = [22.1, 44.2]
    stds = [1, 3]
    with RdbApi(db_session) as rdb_api, BlobApi(db_session) as blob_api:
        key_indexes_df = blob_api.add_blob(data=key_indexes)
        data_indexes_df = blob_api.add_blob(data=data_indexes)
        values_df = blob_api.add_blob(data=values)
        stds_df = blob_api.add_blob(data=stds)
        blob_api.commit()

        observation = rdb_api.add_observation(
            name=observation_name,
            key_indexes_ref=key_indexes_df.id,
            data_indexes_ref=data_indexes_df.id,
            values_ref=values_df.id,
            stds_ref=stds_df.id,
        )
        rdb_api.commit()
        assert observation is not None

    with RdbApi(db_session) as rdb_api, BlobApi(db_session) as blob_api:
        observation = rdb_api.get_observation(observation_name)
        assert observation is not None
        assert (
            blob_api.get_blob(observation.key_indexes_ref).data == key_indexes
        )
        assert (
            blob_api.get_blob(observation.data_indexes_ref).data == data_indexes
        )
        assert blob_api.get_blob(observation.values_ref).data == values
        assert blob_api.get_blob(observation.stds_ref).data == stds


def test_add_duplicate_observation(db_session):
    with RdbApi(db_session) as rdb_api:
        rdb_api.add_observation(
            name="test",
            key_indexes_ref=1,
            data_indexes_ref=1,
            values_ref=1,
            stds_ref=1,
        )
        rdb_api.commit()

        with pytest.raises(sqlalchemy.exc.IntegrityError) as error:
            rdb_api.add_observation(
                name="test",
                key_indexes_ref=2,
                data_indexes_ref=2,
                values_ref=2,
                stds_ref=2,
            )
            rdb_api.commit()


def test_add_response(db_session):
    indexes = [0, 2]
    values = [22.1, 44.2]
    with RdbApi(db_session) as rdb_api, BlobApi(db_session) as blob_api:
        indexes_df = blob_api.add_blob(data=indexes)
        values_df = blob_api.add_blob(data=values)
        blob_api.commit()

        ensemble = rdb_api.add_ensemble(name="test")

        response_definition = rdb_api.add_response_definition(
            name="test", indexes_ref=indexes_df.id, ensemble_name=ensemble.name
        )

        realization = rdb_api.add_realization(0, ensemble.name)

        response = rdb_api.add_response(
            name=response_definition.name,
            values_ref=values_df.id,
            realization_index=realization.index,
            ensemble_name=ensemble.name,
        )
        rdb_api.commit()

    with RdbApi(db_session) as rdb_api, BlobApi(db_session) as blob_api:
        ensemble = rdb_api.get_ensemble(name="test")
        assert ensemble.id is not None
        response_definition = rdb_api._get_response_definition(
            name="test", ensemble_id=ensemble.id
        )
        assert response_definition.id is not None
        assert response_definition.ensemble_id is not None
        assert (
            blob_api.get_blob(id=response_definition.indexes_ref).data
            == indexes
        )

        realization = rdb_api.get_realization(index=0, ensemble_name=ensemble.name)
        assert realization.id is not None
        assert realization.ensemble_id is not None

        response = rdb_api.get_response(
            response_definition.name, realization.index, ensemble.name
        )
        assert response.id is not None
        assert response.realization_id is not None
        assert response.response_definition_id is not None
        assert blob_api.get_blob(id=response.values_ref).data == values


def test_add_ensemble(db_session):
    with RdbApi(db_session) as rdb_api:
        ensemble = rdb_api.add_ensemble(name="test_ensemble")
        rdb_api.commit()
        assert ensemble.id is not None

        with pytest.raises(sqlalchemy.exc.IntegrityError) as error:
            rdb_api.add_ensemble(name="test_ensemble")
            rdb_api.commit()


def test_add_realization(db_session):
    with RdbApi(db_session) as rdb_api:
        ensemble = rdb_api.add_ensemble(name="test_ensemble")

        realizations = []
        for i in range(5):
            realization = rdb_api.add_realization(i, ensemble.name)
            realizations.append(realization)

        rdb_api.commit()

        assert ensemble.id is not None
        for realization in realizations:
            assert realization.id is not None

    with pytest.raises(sqlalchemy.exc.IntegrityError) as error, RdbApi(
        session=db_session
    ) as rdb_api:
        rdb_api.add_realization(0, ensemble_name=ensemble.name)
        rdb_api.commit()


def test_add_parameter(db_session):
    value = 22.1

    with RdbApi(db_session) as rdb_api, BlobApi(db_session) as blob_api:
        value_df = blob_api.add_blob(data=value)
        blob_api.commit()

        ensemble = rdb_api.add_ensemble(name="test")

        parameter_definition = rdb_api.add_parameter_definition(
            name="test_param", group="test_group", ensemble_name=ensemble.name
        )

        realization = rdb_api.add_realization(0, ensemble.name)

        parameter = rdb_api.add_parameter(
            name=parameter_definition.name,
            group=parameter_definition.group,
            value_ref=value_df.id,
            realization_index=realization.index,
            ensemble_name=ensemble.name,
        )
        rdb_api.commit()

    with RdbApi(db_session) as rdb_api, BlobApi(db_session) as blob_api:
        ensemble = rdb_api.get_ensemble(name="test")
        assert ensemble.id is not None

        parameter_definition = rdb_api._get_parameter_definition(
            name="test_param", group="test_group", ensemble_id=ensemble.id
        )
        assert parameter_definition.id is not None
        assert parameter_definition.ensemble_id is not None

        realization = rdb_api.get_realization(index=0, ensemble_name=ensemble.name)
        assert realization.id is not None
        assert realization.ensemble_id is not None

        parameter = rdb_api.get_parameter(
            name="test_param", group="test_group", realization_index=0, ensemble_name=ensemble.name
        )
        assert parameter.id is not None
        assert parameter.realization_id is not None
        assert parameter.parameter_definition_id is not None
        assert blob_api.get_blob(id=parameter.value_ref).data == value