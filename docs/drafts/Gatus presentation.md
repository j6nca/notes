Hey folks, Im Jonathan, a DevOps engineer on the services team. and this week Ill be giving you a brief overview of Gatus, which we recently migrated to ECS and you can access it behind the VPN on status.stackadapt.dev

so to start off, endpoint configurations for gatus are currently managed centrally in the infra repo and teams are encouraged to add or update these endpoints as needed

so from the Gatus UI, you can see a simplified overview of recent endpoint checks,

but for a more comprehensive view of these results, I would suggest using the dashboard in Grafana which you can find by just searching 'Gatus' that gives you more insights and flexibility in querying and displaying said information

### NEXT SLIDE

alerts?
Now what about alerts? so in terms of getting started, teams can just add the endpoint configuration and gatus will alert  out of the box, we have a generic alert rule setup for all endpoints that gatus monitors, and it uses the `owner_team` value to route accordingly. 

This can be customized further down the road if needed. 

and Gatus also has its own built-in alerting functionality which we may evaluate in the future as a fall-back alternative

### NEXT SLIDE

Now Ill talk a bit about some planned additions we want to bring to gatus in the future:

- We're looking to provide better support for endpoint monitoring across regions, currently it is running in us-east-1 which makes the latency readings for endpoints in other regions less valuable in terms of actioning alerts
- And we are also looking into ways to enable auto-discovery of service endpoints for gatus to monitor which will simplify having to manually manage and update these endpoints in the future

ill  open the floor any questions?

if there are any further questions or you are curious about updates, feel free to check out the `#eng-ops-observability` channel! Thanks for your time and Ill hand it off to Daniel!