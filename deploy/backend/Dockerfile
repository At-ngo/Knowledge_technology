FROM maven:3.9.9-eclipse-temurin-17 AS build

WORKDIR /app

COPY Knowledge_technology/legalqa-engine/pom.xml ./pom.xml
COPY Knowledge_technology/legalqa-engine/src ./src

RUN mvn -B -DskipTests clean package

FROM eclipse-temurin:17-jre

WORKDIR /app

COPY --from=build /app/target/*.jar /app/app.jar

EXPOSE 8080

ENTRYPOINT ["java", "-jar", "/app/app.jar"]
