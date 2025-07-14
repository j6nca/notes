Helm templating works off the Golang Sprig library. Documenting here some handy templating usecases:

# Reusing values (keep it DRY)

Lets say your values file requires several references to a name of a service. You can leverage yaml anchors to keep this DRY as to make updates more manageable and simple.

```yaml
# values.yml
metadata: &metadata
  owner_team: my_team
  service: &service my_service
  
  
service_name: *service
labels: 
  <<: *metadata
annotations:
  <<: *metadata
```

```yaml
# template.yml
labels: {{ toYaml .Values.metadata | nindent 2 }}
```

```yaml
# output.yml
labels:
  owner_team: my_team
  service: my_service
```

# Assign sub-values map directly to template:

This is handy when working with large blocks of annotations & labels that you want to consume (either in a helpers file or directly in your manifests).

```yaml
# values.yml
metadata:
  owner_team: my_team
  service: my_service
```

```yaml
# template.yml
labels: {{- toYaml .Values.metadata | nindent 2 }}
```

```yaml
# output.yml
labels:
  owner_team: my_team
  service: my_service
```