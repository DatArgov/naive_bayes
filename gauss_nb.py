# -*- coding: utf-8 -*-
import random
import csv
from collections import defaultdict
from math import e
from math import pi
import requests
import re


class GaussNB:

    def __init__(self, normalize=False, standardize=False):
        self.summaries = {}
        self.normalize = normalize
        self.standardize = standardize

    def load_csv(self, data, clean='', header=False, rows=0, delimiter=','):
        """
        :param data:
        :param clean:
        :param header:
        :param rows:
        :param delimiter:
        :return:
        Load and convert each string of data into float
        """
        lines = csv.reader(data.splitlines(), delimiter=delimiter)
        dataset = list(lines)
        if header:
            # remove header
            dataset = dataset[1:]
        if rows:
            dataset = dataset[:rows]
        if clean in ['adult']:
            for i in range(len(dataset)):
                if not dataset[i]:
                    # skipping empty rows
                    continue
                sex = dataset[i][9].lower().strip()
                dataset[i] = [float(re.search('\d+', x).group(0)) for x in dataset[i] if re.search('\d+', x)]
                dataset[i].append(sex)
        elif clean in ['iris', 'diabetes', 'redwine']:
            for i in range(len(dataset)):
                dataset[i] = [float(x) if re.search('\d', x) else x for x in dataset[i]]
        else:
            print 'Add dataset.'
            return None
        return dataset

    def normalize_data(self, data):
        minimum = min(data)
        maximum = max(data)
        min_max = minimum - maximum
        result = [abs((i - minimum) / min_max) for i in data]
        return result

    def standardize_data(self, data):
        stdev = self.stdev(data)
        avg = self.mean(data)
        result = [(i - avg) / stdev for i in data]
        return result

    def split_data(self, data, weight):
        """
        :param data:
        :param weight: indicates the percentage of rows that'll be used for testing
        :return:
        Randomly select rows for testing.
        """
        train_size = int(len(data) * weight)
        train_set = []
        for i in range(train_size):
            index = random.randrange(len(data))
            train_set.append(data[index])
            data.pop(index)
        return [train_set, data]

    def mean(self, numbers):
        result = sum(numbers) / float(len(numbers))
        return result

    def stdev(self, numbers):
        """
        :param numbers: list of numbers
        :return:
        Calculate the standard deviation for a list of numbers.
        """
        avg = self.mean(numbers)
        squared_diff_list = []
        for num in numbers:
            squared_diff = (num - avg) ** 2
            squared_diff_list.append(squared_diff)
        squared_diff_sum = sum(squared_diff_list)
        sample_n = float(len(numbers) - 1)
        var = squared_diff_sum / sample_n
        return var ** .5

    def group_by_class(self, data, target):
        """
        :param data: Training set. Lists of events (rows) in a list
        :param target: Index for the target column. Usually the last index in the list
        :return:
        Mapping each target to a list of it's features
        """
        target_map = defaultdict(list)
        for index in range(len(data)):
            features = data[index]
            if not features:
                continue
            x = features[target]
            target_map[x].append(features[:-1])
        print 'Identified %s different target classes: %s' % (len(target_map.keys()), target_map.keys())
        return dict(target_map)

    def summarize(self, data):
        """
        :param data: lists of events (rows) in a list
        :return:
        Use zip to line up each feature into a single column across multiple lists.
        yield the mean and the stdev for each feature
        """
        for attributes in zip(*data):
            if self.normalize:
                attributes = self.normalize_data(attributes)
            if self.standardize:
                attributes = self.standardize_data(attributes)
            yield {
                'stdev': self.stdev(attributes),
                'mean': self.mean(attributes)
            }

    def train(self, train_list, target):
        """
        :param data:
        :param target: target class
        :return:
        For each target:
            1. yield prior: the probability of each class. P(class) eg P(Iris-virginica)
            2. yield summary: list of {'mean': 0.0, 'stdev': 0.0}
        """
        group = self.group_by_class(train_list, target)
        self.summaries = {}
        for target, features in group.iteritems():
            self.summaries[target] = {
                'prior': self.prior_prob(group, target, train_list),
                'summary': [i for i in self.summarize(features)],
            }
        return self.summaries

    def prior_prob(self, group, target, data):
        """
        :return:
        The probability of each target class
        """
        total = float(len(data))
        result = len(group[target]) / total
        return result

    def normal_pdf(self, x, mean, stdev):
        """
        :param x: a variable
        :param mean: µ - the expected value or average from M samples
        :param stdev: σ - standard deviation
        :return: Gaussian (Normal) Density function.
        N(x; µ, σ) = (1 / 2πσ) * (e ^ (x–µ)^2/-2σ^2
        """
        variance = stdev ** 2
        exp_squared_diff = (x - mean) ** 2
        exp_power = -exp_squared_diff / (2 * variance)
        exponent = e ** exp_power
        denominator = ((2 * pi) ** .5) * stdev
        pdf = exponent / denominator
        return pdf

    def get_prediction(self, test_vector):
        """
        :param test_vector: single list of features to test
        :return:
        Return the target class with the largest/best posterior probability
        """
        posterior_probs = self.posterior_probabilities(test_vector)
        best_target = max(posterior_probs, key=posterior_probs.get)
        return best_target

    def posterior_probabilities(self, test_vector):
        """
        :param test_vector: single list of features to test
        :return:
        For each feature (x) in the test_vector:
            1. Calculate Predictor Prior Probability using the Normal PDF N(x; µ, σ). eg = P(feature | class)
            2. Calculate Likelihood by getting the product of the prior and the Normal PDFs
            3. Multiply Likelihood by the prior to calculate the Joint PDF. P(Iris-virginica)

        E.g.
        prior: P(setosa)
        likelihood: P(sepal length | setosa) * P(sepal width | setosa) * P(petal length | setosa) * P(petal width | setosa)
        numerator (joint pdf): prior * likelihood
        denominator (marginal pdf): predictor prior probability
        posterior_prob = joint pdf/ marginal pdf

        returning a dictionary mapping of class to it's posterior probability
        """
        posterior_probs = {}
        for target, features in self.summaries.iteritems():
            total_features = len(features['summary'])
            likelihood = 0
            pdfs = []
            for index in range(total_features):
                mean = features['summary'][index]['mean']
                stdev = features['summary'][index]['stdev']
                x = test_vector[index]
                normal = self.normal_pdf(x, mean, stdev)
                likelihood = posterior_probs.get(target, 1) * normal
                pdfs.append(normal)
            marginal = self.marginal_pdf(pdfs)
            prior = features['prior']
            posterior_probs[target] = (prior * likelihood) / marginal
        return posterior_probs

    def marginal_pdf(self, pdfs):
        """
        :param pdfs: list of probability densities for each feature
        :return:
        Marginal Probability Density Function (Predictor Prior Probability)
        Summing up the product of P(class) prior probability and the probability density of each feature P(feature | class)

        marginal pdf =
          P(setosa) * P(sepal length | setosa) + P(versicolour) * P(sepal length | versicolour) + P(virginica) * P(sepal length | verginica)
        + P(setosa) * P(sepal width | setosa) + P(versicolour) * P(sepal width | versicolour) + P(virginica) * P(sepal width | verginica)
        + P(setosa) * P(petal length | setosa) + P(versicolour) * P(petal length | versicolour) + P(virginica) * P(petal length | verginica)
        + P(setosa) * P(petal length | setosa) + P(versicolour) * P(petal length | versicolour) + P(virginica) * P(petal length | verginica)
        """
        predictors = []
        for target, features in self.summaries.iteritems():
            prior = features['prior']
            for index in range(len(pdfs)):
                normal_pdf = pdfs[index]
                predictors.append(prior * normal_pdf)
        marginal_pdf = sum(predictors)
        return marginal_pdf

    def predict(self, test_set):
        """
        :param test_set: list of features to test on
        :return:
        Predict the likeliest target for each row of the test_set.
        Return a list of predicted targets.
        """
        predictions = []
        for row in test_set:
            result = self.get_prediction(row)
            predictions.append(result)
        return predictions

    def accuracy(self, test_set, predicted):
        """
        :param test_set: list of test_data
        :param predicted: list of predicted classes
        :return:
        Calculate the the average performance of the classifier.
        """
        correct = 0
        actual = [item[-1] for item in test_set]
        for x, y in zip(actual, predicted):
            if x == y:
                correct += 1
        return correct / float(len(test_set))


def main():
    """
    :return:
    Training and testing data
    """
    urls = {
        'iris': 'http://archive.ics.uci.edu/ml/machine-learning-databases/iris/iris.data',  # ~ 94% accurracy
        'diabetes': 'https://archive.ics.uci.edu/ml/machine-learning-databases/pima-indians-diabetes/pima-indians-diabetes.data',  # ~ 76% accuracy
        'redwine': 'http://archive.ics.uci.edu/ml/machine-learning-databases/wine-quality/winequality-red.csv',  # ~ 34% accuracy
        'adult': 'http://archive.ics.uci.edu/ml/machine-learning-databases/adult/adult.data'  # ~ 65% accuracy. varries with sample sizes
    }
    weight = 0.67
    for title, url in urls.iteritems():
        nb = GaussNB()
        data = requests.get(url).content
        print '\n ************ \n'
        print 'Executing: %s dataset' % title
        if title in ['iris', 'diabetes']:
            data = nb.load_csv(data, clean=title, header=False, rows=False, delimiter=',')
        elif title in ['redwine']:
            data = nb.load_csv(data, clean=title, header=True, rows=False, delimiter=';')
        elif title in ['adult']:
            data = nb.load_csv(data, clean=title, header=True, rows=10000, delimiter=',')
        else:
            print 'Add title and url.'
            break
        train_list, test_list = nb.split_data(data, weight)
        print 'Split %s rows into train=%s and test=%s rows' % (len(data), len(train_list), len(test_list))
        nb.train(train_list, -1)
        predicted_list = nb.predict(test_list)
        accuracy = nb.accuracy(test_list, predicted_list)
        print 'Accuracy: %.3f' % accuracy


if __name__ == '__main__':
    main()
