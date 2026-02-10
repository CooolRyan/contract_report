# 1) Spring Boot JAR 빌드 (gradle wrapper 없으면 공식 gradle 이미지 사용)
FROM gradle:8.5-jdk17-alpine AS builder
WORKDIR /app

COPY build.gradle settings.gradle ./
RUN gradle dependencies --no-daemon || true

COPY src src
RUN gradle bootJar --no-daemon -x test

# 2) 실행용 이미지
FROM eclipse-temurin:17-jre-alpine
WORKDIR /app

RUN adduser -D -u 1000 appuser
COPY --from=builder /app/build/libs/*.jar app.jar
RUN chown -R appuser:appuser /app

USER appuser
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
