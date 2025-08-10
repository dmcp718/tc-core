# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview
TC-NGINX is a high-performance, distributed NGINX caching solution designed for 100TB+ storage capacity. It uses Docker Compose to orchestrate a load balancer, multiple cache nodes, and comprehensive monitoring with Prometheus and Grafana.

## Common Commands

### Deployment & Management
```bash
# Start entire stack
docker-compose up -d

# Rebuild and restart services
docker-compose down && docker-compose up -d --force-recreate

# View logs for specific services
docker-compose logs -f nginx-lb      # Load balancer logs
docker-compose logs -f nginx-cache-1 # Cache node logs

# Stop all services
docker-compose down
```

### Health Checks & Monitoring
```bash
# Check service health
curl http://localhost:8013/health  # Load balancer
curl http://localhost:8081/health  # Cache node 1
curl http://localhost:8082/health  # Cache node 2
curl http://localhost:8083/health  # Cache node 3
curl http://localhost:8084/health  # Cache node 4

# View cache statistics
curl http://localhost:8081/cache-stats
curl http://localhost:8082/cache-stats
curl http://localhost:8083/cache-stats
curl http://localhost:8084/cache-stats

# Access monitoring dashboards
http://localhost:9090  # Prometheus
http://localhost:3000  # Grafana (check for "NGINX Cache Overview" dashboard)
```

## Architecture

### Load Balancing Layer
- **File**: `nginx-lb.conf`
- **Purpose**: Routes requests to cache nodes using consistent hashing
- **Key Behavior**: 
  - GET/HEAD requests → Cache cluster with hash-based routing
  - PUT/POST/DELETE → Direct proxy to origin
  - Implements failover and health checking

### Caching Layer
- **File**: `nginx-cache.conf` (shared by all cache nodes)
- **Nodes**: 4 cache instances (nginx-cache-1 through nginx-cache-4)
- **Storage**: Each node manages 4 disks with 25TB capacity each
- **Cache Zones**: 
  - `s3_cache_1` → `/cache/disk1`
  - `s3_cache_2` → `/cache/disk2`
  - `s3_cache_3` → `/cache/disk3`
  - `s3_cache_4` → `/cache/disk4`
- **Key Distribution**: URI hash determines which disk stores each object

### Monitoring Stack
- **Prometheus**: Collects metrics from NGINX exporters (`conf/prometheus.yml`)
- **Grafana**: Visualizes metrics (`conf/grafana/grafana.ini`, `conf/grafana/dashboards/`)
- **Exporters**: Each cache node has a Prometheus exporter (ports 9101-9104)

### Performance Optimizations
- Direct I/O for large files (>10MB)
- Asynchronous I/O enabled
- Sendfile for efficient data transfer
- TCP optimizations (nodelay, nopush)
- Worker process per CPU core

### Request Flow
1. Client → Load Balancer (port 8013)
2. Load Balancer hashes URI to select cache node
3. Cache node checks local storage across 4 disks
4. On miss: Fetches from origin S3 bucket
5. Caches response for 24 hours (successful responses)
6. Returns cached or fresh content to client

## Key Configuration Files
- `docker-compose.yml` - Service orchestration
- `nginx-lb.conf` - Load balancer configuration
- `nginx-cache.conf` - Cache node template
- `conf/prometheus.yml` - Metrics collection
- `conf/grafana/dashboards/nginx-cache-dashboard.json` - Pre-built dashboard

## Important Notes
- Total system capacity: 400TB (100TB per cache node)
- Cache validity: 24 hours for 200/206/301/302 responses
- AWS signatures are passed through (not cached)
- Health endpoints available for all services
- Monitoring stack provides real-time performance insights