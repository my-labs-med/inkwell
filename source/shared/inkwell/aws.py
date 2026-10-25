import functools
import os

import boto3

from inkwell import tracing

tracing.init()


@functools.cache
def dynamodb():
    return boto3.resource("dynamodb")


@functools.cache
def tasks_table():
    return dynamodb().Table(os.environ["TASKS_TABLE"])


@functools.cache
def stats_table():
    return dynamodb().Table(os.environ["STATS_TABLE"])


@functools.cache
def ses():
    return boto3.client("ses")


@functools.cache
def cognito():
    return boto3.client("cognito-idp")


def reset():
    for factory in (dynamodb, tasks_table, stats_table, ses, cognito):
        factory.cache_clear()
