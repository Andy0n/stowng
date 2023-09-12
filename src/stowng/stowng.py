# -*- coding: utf-8 -*-
import argparse

def main():
    parser = argparse.ArgumentParser(
        prog='StowNG',
        description='StowNG is GNU Stow in Python',
    )

    args = parser.parse_args()
    print('Hello, StowNG!')
