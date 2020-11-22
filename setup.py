import setuptools

with open("README.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="protobuf-inspector",
    version="0.2",
    author="Alba Mendez",
    author_email="me@alba.sh",
    description="Tool to reverse-engineer Protocol Buffers with unknown definition",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/mildsunrise/protobuf-inspector",
    packages=setuptools.find_packages(),
    entry_points={
        'console_scripts': [
            'protobuf_inspector=protobuf_inspector.__main__:main',
        ],
    },
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: ISC License (ISCL)",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.3',
)
