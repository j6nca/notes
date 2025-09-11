# Background

# Requirements

## Components

- Metrics (VictoriaMetrics)
- Logs (Grafana Loki)
- Profiling (Grafana Pyroscope)
- Tracing (Grafana Tempo)
- OTEL Collector (Grafana Alloy)
- 

monitoring vs observability

sli and slos

dash board with example hands on walk through

profiling tracing

1hr 15min

google the art of SLO's

grafana get started -> tracaes, etc docker-compose examples

pin versions so things are consistent. 

if we need to chop - alerting sli slos skim it down good signals


just to preface this, we are in a bit of time crunch as we want to cover a lot of things in this session so if we dont get to any questions feel free to drop them in our observability channel: `#eng-ops-observability`


[https://grafana.com/docs/pyroscope/latest/get-started/ride-share-tutorial/](https://grafana.com/docs/pyroscope/latest/get-started/ride-share-tutorial/)[https://grafana.com/docs/tempo/next/docker-example/](https://grafana.com/docs/tempo/next/docker-example/)  
[https://github.com/grafana/tempo/tree/main/example/docker-compose](https://github.com/grafana/tempo/tree/main/example/docker-compose)

This might be useful https://github.com/grafana/intro-to-mltp

#  Breakdown

- Intro, services [5min]
- Setup / run local stack [5min]
	- Ensure folks have pulled images/local dependencies beforehand (`docker compose pull`) to make this seamless
- Concepts & workshopping (highlighting any key points below) [55min]
	- Metrics walkthrough
		- Querying basics and considerations
	- Metrics session
		- Build a dashboard
	- Logging walkthrough
	- Logging session
	- Profiling walkthrough
	- Profiling session
	- Traces walkthrough
	- Traces session
	- Alerting walkthrough
		- SLI, SLOs, golden signals, noise reduction
	- Alerting session
		- Common alert query example and applying noise reduction there
- Wrap up and closing remarks [5min]

# Workshopping

Context, you're running a kitchen store, and you have an app for customers and also an api which relays info from storage about products and various other things in the store.

Customers are trying to reach your app, and are noticing a sizeable delay.



# References

- https://cloud.google.com/blog/products/devops-sre/sre-fundamentals-slis-slas-and-slos
- https://grafana.com/blog/2022/04/01/get-started-with-metrics-logs-and-traces-in-our-new-grafana-labs-asia-pacific-webinar-series/
- https://www.youtube.com/watch?v=fMkoJpSByV8
- https://www.youtube.com/watch?v=qVITI34ZFuk
- https://squaredup.com/blog/metrics-vs-logs-vs-traces-vs-profiles/
- https://sre.google/sre-book/monitoring-distributed-systems/


# Presentation

- close all irrelevant tabs
- presenter mode
- share entire chrome window

## Introduction

Hey everyone my name is Jonathan and Im from the eng-ops services team, 
Im excited to be hosting this working session on the observability stack today

## Workshop Overview

So in today's session we're hoping to cover quite a bit. We will start with a brief setup window so that everyone is up-to-date and running their demo stacks.

We will then briefly go over observability components and some common terms before diving in to these components individually

Each section we cover here will have a small workshop and/or walkthrough component to help solidify understandings and topics

and We will end it off with closing remarks and questions

## Setup

So lets start off by giving folks a few minutes to start up their stacks.

before anything please do a `git pull` to get the latest changes as the repo has changed quite a bit.

If you havent already done so the repo link is up top, please clone and run the commands under the `Setup` section.

## Components Overview

We will be covering metrics, logs, traces and profiling. 

Each of these components brings different value when looking at observability and can be combined to enhance derived insights into systems.

For relevance to our own setup - currently we use:

Victoriametrics as our metrics backend
Loki for logging
Tempo for traces
Pyroscope for profiling
AlertManager for alert routing
and to collect all of this data we are running Grafana alloy

These are also the services we've just spun up locally for the working session.

## Monitoring vs Observability

So, Often we see these two terms thrown around interchangeably and thats generally fine, but I wanted to provide some more insight into the difference between monitoring and observability

Monitoring on one hand focuses on "the known", these are predefined and expected scenarios that we can account for and anticipate to come up. 

We can reactively build alerts off of these known signals and indicators to let us know if something is wrong.

Observability is using these components (so metrics, logs, traces, profiles) to answer novel questions, scenarios we may have not expected. These tools allow us to approach and get a better understanding of problems we have not seen before.

In a way this is sort of a loop and the answers we derive from an observability question may lead to additions to monitoring.

## Metrics

First component we will talk about is metrics, metrics provide a numerical representation of systems, common examples being memory usage, latency, throughput

These are useful in trend analysis, understanding system state via dashboards, and also for alerting

## Metrics - types

There are a few different types of metrics 

those include the counter, gauge and histogram

A counter metrics is a cumulative measure that can only increase for the duration of runtime think totals etc.

Metrics that might fluctuate in value shouldnt be using counters. so what should they use? Thats where the next type comes in - gauges, essentially the counter but with values that can move both directions.

Lastly we also have the histogram metric type, this one is a bit unique compared to the others as alongside it, it exposes three time-series, the histogram metric samples numerical observations into configured buckets

An analogy to illustrate these different metric types is a dashboard you might find in your car

we have various signals and information captured via sensors which symbolize metric collection

speedometer would be a gauge type metric

odometer or total miles tracker would be a counter

## Metrics - 4 Golden signals

Next we will go over the 4 golden signals in metrics. These are key identifiers in understanding the performance and health of systems and include measurements for 

- latency or duration of requests
- traffic or throughput  - such as requests per second
- errors -  out of the volume of requests coming in how much of it result in errors?
- and saturation, or how "full" a system is, which may be an indicator of capacity and or resource issues such as over or under provisioning

You may have also heard of RED monitoring which similarly covers Rate (or traffic), errors, and duration (or latency) skipping over saturation.

## Metrics - Cardinality

NExt we will talk about a common pain point in metrics systems - 
Cardinality also known as the dimension problem.   

Cardinality refers to the number of unique combinations of labels associated with a metric. the higher cardinality, the worse the performance.

An example of this would be attaching unique identifiers to label values causing a surge in unique time series stored

the Rule of thumb here - is to avoid these unique identifiers and only assign the labels that you need to filter on.

## Metrics - Do's and Dont's

Some other best practices here include

- adding appropriate label filters when making queries, to minimize the data needed to scan and achieve faster result retrieval
- use recording rules for slow/complex and or frequently used queries these will get pre-computed and stored as their own metric for faster querying
- following standardization set across the org (metadata, labels) - consistency and organization is key!

## Metrics - Workshop

Now we will start with the first workshop. 

For the walkthrough - we'll largely be using the `Rideshare Example` dashboard provisioned under `Monitoring Workshop` and building on top of that. Lets head over to our local grafana on port 3000, and lets keep this tab open for the duration of this session as we will be referencing it quite a bit. 

Under the Monitoring Workshop folder, you will find this dashboard along with another suffixed with "Reference", this "Reference" dashboard is there so everyone has a copy of what the modified queries in the end will look like (spoiler alert)
you don't need to open it, but its there as a reference in case you missed anything along the way as we make changes to the primary dashboard.

Let's take a look at this requests visualization, we are using a counter metric called `go_app_http_requests_total` to display requests coming in. Based on what we discussed above, what might be a problem with this visualization?

so The issue with this query is it solely captures the counter metric value - a value that doesn't provide us much context on the system as it will only show us an ever-incrementing number of requests from start time - and this makes trend analysis hard to do,- theres no indicator of if we currently have a high volume of traffic or if that may have been a day ago, or if the requests have just been steadily increasing over time. The value also doesn't persist after a restart which may cause confusion as to what is being measured. 

We can illustrate this happening too - if we restart any of the `rideshare-apps` and look at the graph, you will see a dip equivalent to the counter resetting to 0. Even prior to the flatline, we cant really form any conclusions - especially when we deal with higher and higher volumes of traffic (as we do here).


```
docker-compose restart us-east
```

So im going to show that by running docker compose on  the us-east service and we can watch the graph update

Now we'll wait a bit but we expect to see this sum take a dip which is equivalent to the counter resetting for that service to 0.

As you can see the graph has dipped even though there is no visible change in traffic!

That brings us to the question - how can we make this information relevant and usable by us with context persisted through a restart?

The key here and a common pattern we use with counter typed metrics -  is the `rate()` function. This gives us the per-second rate of increase of the `http_requests_total` counter which adjusts for counter resets through  service restarts. 


We arrive at something such as this which gives us the per-second increase in http requests over the last 5 mins.

```
sum(rate(go_app_http_requests_total[5m]))
```

While we're at it, let's go back and add a few more golden signals visualizations. 

So we have stubs for error rates and latency created as well with their respective metrics - but we will apply some functions here to get some usable visualizations.

We will first start with the error rate visualization, but first lets simulate some error requests coming in by running

```
hey -n 200 http://localhost:5050/error
```

For the error rate, we will build off the existing throughput query we just created and calculate a ratio of errors to total requests using the request status codes:

```
sum(rate(go_app_http_requests_total{service_name=~"workshop.*", status_code=~"5.."}[5m]))
/
sum(rate(go_app_http_requests_total{service_name=~"workshop.*"}[5m]))
```

Moving on to the latency query, here, we are using one of the metrics from the histogram of request durations. We are going to create an view based on the average request latency. This can be done by taking the total duration of all requests and dividing by the total number of requests both exposed by the histogram metric.

```
sum(
rate(go_app_http_request_duration_seconds_sum{service_name=~"workshop.*", path!="/favicon.ico"}[5m])
/
rate(go_app_http_request_duration_seconds_count{service_name=~"workshop.*", path!="/favicon.ico"}[5m])
) by (path)
```

This gives us a good overview of all the latencies we are seeing across endpoints, as you can tell, the avg latency for the car endpoint is higher than the others and we will dig into that later on.

## Logging

Next we have logging - logging captures records of events in chronological order which provide us with more context as to what is happening

this additional info doesnt come without the drawback of being less storage efficient especially compared to metrics and therefore more costly as well

## Logging - Considerations

Some considerations to account for when designing your logs:

- Only log what you need
	- You want to avoid unnecessary log volume or overly verbose logs as that would be expensive to store and query
	- You also want to include context that will help further enhance debugging such as requestIDs, traceIDs, spanIDs etc.
- Set appropriate log levels
	- you might even want different log levels depending on the environment
		- for example, in lower environments you might want higher verbosity to  enhance debugging for quick testing and troubleshooting
- Use structured logging formats such as JSON, which makes logs easier to parse, query and aggregate
- lastly Don't log sensitive data such as passwords and personally identifiable information

## Logging - Workshop

We're going to go back to our workshop dashboard example. 

This time we have 2 logging visualizations, we are going to adjust the filters here to just show us requests on one, and errors on the other.

JSON logs -> filter down on JSON

## Traces

Now we're going to take a look at traces

- Traces let us observe behaviour across multiple systems
- Where logs, metrics, and profiling capture information from one particular system, traces are the bridge between these systems
- There are three components in a trace
	- the trace itself which  makes up the end to end journey of a request
	- there is spans, which are a single unit of work within a trace (so think function calls, http reqs) and span track the time spent on the work
	- and then there are the links between spans to gi

An analogy to understand traces better is think of a package tracking service, information about the package is collected as it moves through countries, customs and local shipping companies.

## Profiling

Profiling looks under the hood into a programs resource usage and gives detailed information on the execution of code

It is complementary alongside traces as traces let you narrow in on problems from a broad perspective and profiling lets you pinpoint where the problem originated (including what function? what line of code?)

We have the option to enable profiling on an adhoc basis, however continuous profiling gives you better context when looking at long term analysis and identifying regressions.



## Traces and Profiling Workshop

Now lets combine all of this and investigate a small simulated scenario with our example rideshare application!

So some context on this example: we have a client which is generating load against our rideshare services which we've simulated to run across 3 regions.

Customers in Europe are reporting slow load times when using the client.

First off, lets jump into our traces visualization, you should see a bunch of traces listed

these are from the requests coming in from our simulated load generator

it looks like the general trend of these trace durations across the board average around 5-600 milliseconds, however there are a few outliers here upwards of 1.5 seconds, lets take a closer look at those

Lets open one of these longer traces in a new tab to get some more info.

We can actually view respective profiling data from the spans that make up these traces as they travel through individual services.

So we can see here that the entire journey of the request takes a few seconds. It spends a few hundred milliseconds on the client before taking the remainder of the time within the ridesharing app. Whats up with that? lets take another closer look

We can open this in profiles drilldown to further break it down. Lets add a label filter here by region - on the left we will have us-east and on the right we will have eu-north and we can further see this discrepancy in cpu usage appear between these regions.

We can also compare the rideshare profile information between these two instances in the flamegraph. 

So a flamegraph for context, is a hierarchical visualization to show time or resources spent and this is indicated by the length of blocks in the graph.

it looks like it calls OrderCar, then FindNearestVehicle, and lastly it lands in a mutexLock which it spends a much longer time compared to the other regions.

We can then dive into the code and take a closer look.

So if we jump into `utility/utility.go`, which is where this is all defined, we can see there are a couple of suspicious lines here used to generate load when the region is eu-north (L54-57). We can comment that out, we'll also need to comment out the `os` import here and we can rebuild this via

```
docker-compose up -d --wait --build
```

After doing all that, and going back into the profiles drilldown tab, we can see these values have evened out.

## Alerts

We're going to take a bit of a step back and discuss metrics again to talk about alerts.

We will also have support for log-based alerting down the road.

Often times you may find your alert signal is noisy or too sensitive. 

## Alerts - Tuning

Alert fatigue is when there is noise from low-severity or false positive alert evaluations resulting in responders ignoring alerts.

This becomes a problem as we dont know when 

## Alerts - Best practices

Some best practices to account for when writing your alerts are:

- Keep your alert rules minimal, simple and deliberate!
- Alerts should directly correlate to actionable events such as adjusting resources, further investigation, and based on some recent events - updating certs!
- Alerts should always be responded with a sense of urgency, if there are cases where an alert can be ignored, we should adjust the rule to only alert when a response is necessary
- Be considerate of the audience for an alert - ideally teams own and respond to all of their alerts, but there may be some scenarios where these rules may be defined cross-team, in those cases ensure that the appropriate responders are aware and know how to handle these alerts when they come up.

## Alerts - Workshop

Lets turn the error rate query we constructed earlier we had earlier into an alert for us!

Lets say we want to trigger an alert when the error rate surpasses 25% of incoming requests.

I've created a visualization at the bottom of the dashboard to just show how the error rate would move in relation to this 25% threshold we've defined.

I've also added this query to the config for vmalert which will evaluate these queries and alert when the rules evaluate to true

Lets simulate some errors via `hey` and check on these alerts.

```
hey -n 200 http://localhost:5050/error
```

While we wait for Grafana to update, we can take a look at this alert rule configuration. You should see it under the `vmalert/rules.yml` in the workshop repo

On grafana we can watch this error rate go up past the threshold and once that does, lets take a look at vmalert and alertmanager!

This shows how we might take any of these visualizations and turn them into monitors for the team

## Questions?

Thats about all i had for this monitoring session, hoping to run a few more in-depth sessions in the future!

Wanted to open the floor for any questions?

## Closing remarks

Thanks everyone for joining, and again if theres any further questions feel free to reach out to the `eng-ops-observability` channel!