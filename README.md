# Voting Web App Using Klein

An example voting web application which demonstrates core concepts of backend web development using [`klein`](https://github.com/twisted/klein).
An API will be provided that allows users to:

* Nominate/add a candidate to vote for
* Vote for a specified candidate

Since `klein` is based on `twisted`, it is asynchronous and async frameworks are misunderstood in the Python community.
I'm hopeig to shed light into techniques that allow developers develope, test, and append functionality using async frameworks.


### RESTful Vote API

A high level overview of the voting enpoint developed in this web app.

| Action | Method | Endpoint |
| --- | --- | --- |
| Get all candidates | GET | /api/candidates |
| Add a candidate | POST | /api/candidate |
| Cast a vote for a candidate | PUT | /api/vote |
