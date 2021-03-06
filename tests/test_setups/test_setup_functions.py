import sys
import hashlib
import time

import openml
import openml.exceptions
from openml.testing import TestBase

from sklearn.ensemble import BaggingClassifier
from sklearn.tree import DecisionTreeClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.naive_bayes import GaussianNB
from sklearn.base import BaseEstimator, ClassifierMixin


def get_sentinel():
    # Create a unique prefix for the flow. Necessary because the flow is
    # identified by its name and external version online. Having a unique
    #  name allows us to publish the same flow in each test run
    md5 = hashlib.md5()
    md5.update(str(time.time()).encode('utf-8'))
    sentinel = md5.hexdigest()[:10]
    sentinel = 'TEST%s' % sentinel
    return sentinel


class ParameterFreeClassifier(BaseEstimator, ClassifierMixin):
    def __init__(self):
        self.estimator = None

    def fit(self, X, y):
        self.estimator = DecisionTreeClassifier()
        self.estimator.fit(X, y)
        self.classes_ = self.estimator.classes_
        return self

    def predict(self, X):
        return self.estimator.predict(X)

    def predict_proba(self, X):
        return self.estimator.predict_proba(X)

    def set_params(self, **params):
        pass

    def get_params(self, deep=True):
        return {}



class TestRun(TestBase):

    def test_nonexisting_setup_exists(self):
        # first publish a non-existing flow
        sentinel = get_sentinel()
        # because of the sentinel, we can not use flows that contain subflows
        dectree = DecisionTreeClassifier()
        flow = openml.flows.sklearn_to_flow(dectree)
        flow.name = 'TEST%s%s' % (sentinel, flow.name)
        flow.publish()

        # although the flow exists (created as of previous statement),
        # we can be sure there are no setups (yet) as it was just created
        # and hasn't been ran
        setup_id = openml.setups.setup_exists(flow)
        self.assertFalse(setup_id)

    def test_existing_setup_exists(self):
        clfs = [ParameterFreeClassifier(),           # zero hyperparemeters
                GaussianNB(),                        # one hyperparameter
                DecisionTreeClassifier(max_depth=5,  # many hyperparameters
                                       min_samples_split=3,
                                       # Not setting the random state will
                                       # make this flow fail as running it
                                       # will add a random random_state.
                                       random_state=1)]

        for classif in clfs:
            # first publish a nonexiting flow
            flow = openml.flows.sklearn_to_flow(classif)
            flow.name = 'TEST%s%s' % (get_sentinel(), flow.name)
            flow.publish()

            # although the flow exists, we can be sure there are no
            # setups (yet) as it hasn't been ran
            setup_id = openml.setups.setup_exists(flow)
            self.assertFalse(setup_id)
            setup_id = openml.setups.setup_exists(flow, classif)
            self.assertFalse(setup_id)

            # now run the flow on an easy task:
            task = openml.tasks.get_task(115)  # diabetes
            run = openml.runs.run_flow_on_task(task, flow)
            # spoof flow id, otherwise the sentinel is ignored
            run.flow_id = flow.flow_id
            run.publish()
            # download the run, as it contains the right setup id
            run = openml.runs.get_run(run.run_id)

            # execute the function we are interested in
            setup_id = openml.setups.setup_exists(flow)
            self.assertEquals(setup_id, run.setup_id)

    def test_get_setup(self):
        # no setups in default test server
        openml.config.server = 'https://www.openml.org/api/v1/xml/'

        # contains all special cases, 0 params, 1 param, n params.
        # Non scikitlearn flows.
        setups = [18, 19, 20, 118]
        num_params = [8, 0, 3, 1]

        for idx in range(len(setups)):
            current = openml.setups.get_setup(setups[idx])
            assert current.flow_id > 0
            if num_params[idx] == 0:
                self.assertIsNone(current.parameters)
            else:
                self.assertEquals(len(current.parameters), num_params[idx])
