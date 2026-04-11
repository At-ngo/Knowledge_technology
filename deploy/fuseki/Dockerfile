FROM eclipse-temurin:21-jre

WORKDIR /opt

RUN apt-get update \
	&& apt-get install -y --no-install-recommends curl \
	&& rm -rf /var/lib/apt/lists/*

COPY apache-jena-fuseki-6.0.0 /opt/fuseki
COPY Knowledge_technology/reasoning/legal_inference.rules /data/config/legal_inference.rules
COPY Knowledge_technology/reasoning/fuseki-config-inference-docker.ttl /data/config/fuseki-config-inference-docker.ttl
COPY Knowledge_technology/ontology/legal_ontology.rdf /data/input/legal_ontology.rdf
COPY Knowledge_technology/legal_triples.ttl /data/input/legal_triples.ttl
COPY Knowledge_technology/deploy/fuseki/start-fuseki.sh /usr/local/bin/start-fuseki.sh

RUN chmod +x /usr/local/bin/start-fuseki.sh

EXPOSE 3030

ENTRYPOINT ["/usr/local/bin/start-fuseki.sh"]
