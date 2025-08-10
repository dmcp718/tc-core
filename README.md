# TC-Core

High-performance distributed NGINX caching solution with S3 origin support.

## Overview

TC-Core is a scalable caching infrastructure that provides:
- Load balancing with consistent hashing
- Multiple cache node support
- Range request handling for large files
- Comprehensive monitoring with Prometheus and Grafana
- Docker Compose orchestration

## Architecture

The system consists of:
- **Load Balancer**: Distributes requests across cache nodes using URI-based consistent hashing
- **Cache Nodes**: NGINX instances with persistent storage for cached content
- **Monitoring Stack**: Prometheus metrics collection and Grafana dashboards
- **Metrics Exporter**: Custom Python service for cache statistics

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Network access to S3 origin
- Sufficient storage for cache volumes

### Configuration

1. Set your S3 bucket endpoint in the NGINX configurations:
   - `nginx-lb.conf`: Update upstream origins
   - `nginx-cache.conf`: Configure proxy_pass targets

2. Adjust cache storage paths in `docker-compose.yml` to match your disk configuration

### Deployment

```bash
# Start the full stack
docker-compose up -d

# Or use the 2-node configuration
docker-compose -f docker-compose-2node.yml up -d

# View logs
docker-compose logs -f

# Stop services
docker-compose down
```

## Monitoring

Access the monitoring interfaces:
- Grafana: http://localhost:3000
- Prometheus: http://localhost:9090

Health check endpoints:
- Load Balancer: http://localhost:8013/health
- Cache Nodes: http://localhost:808X/health (where X is the node number)

## Configuration Files

- `nginx-lb.conf`: Load balancer configuration
- `nginx-cache.conf`: Cache node template
- `docker-compose.yml`: Multi-node orchestration
- `docker-compose-2node.yml`: 2-node configuration
- `conf/`: Monitoring stack configurations

## Features

- **Consistent Hashing**: Ensures cache efficiency across nodes
- **Range Request Support**: Handles partial content requests
- **Direct I/O**: Optimized for large file transfers
- **Health Monitoring**: Built-in health check endpoints
- **Dynamic Metrics**: Automatic detection of active cache nodes
- **Persistent Storage**: Cache survives container restarts

## Performance Tuning

The system is optimized for:
- High-throughput network operations
- Large file caching and delivery
- Minimal latency for cache hits
- Efficient memory usage

## License

[Specify your license here]

## Contributing

[Add contribution guidelines if applicable]