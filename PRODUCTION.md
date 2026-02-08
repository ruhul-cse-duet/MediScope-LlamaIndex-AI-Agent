# Production Deployment Checklist

## Pre-Deployment

### 1. Configuration
- [ ] Copy `.env.example` to `.env` and configure all settings
- [ ] Set `ENVIRONMENT=production`
- [ ] Set `DEMO_MODE=false`
- [ ] Configure allowed origins (no wildcards in production)
- [ ] Set appropriate `LOG_LEVEL` (WARNING or ERROR for production)
- [ ] Enable file logging: `ENABLE_FILE_LOGGING=true`

### 2. Security
- [ ] Never commit `.env` file to version control
- [ ] Use strong API keys
- [ ] Implement rate limiting (add reverse proxy with rate limits)
- [ ] Enable HTTPS (use reverse proxy like Nginx)
- [ ] Review CORS settings
- [ ] Validate all user inputs
- [ ] Implement authentication/authorization if needed

### 3. Provider Configuration
- [ ] Choose production-ready LLM provider (openai or vllm with proper GPU setup)
- [ ] Configure STT provider if voice features needed
- [ ] Configure TTS provider if voice output needed
- [ ] Configure vision provider if image analysis needed
- [ ] Test all configured providers before deployment

### 4. Dependencies
- [ ] Install core dependencies: `pip install -r backend/requirements.txt`
- [ ] Install ML dependencies if using: `pip install -r backend/requirements-ml.txt`
- [ ] Verify system dependencies:
  - Tesseract OCR (if using OCR)
  - FFmpeg (if using audio)
  - CUDA drivers (if using GPU)

### 5. Database/Storage
- [ ] Ensure `data/` directory exists and has proper permissions
- [ ] Ensure `logs/` directory exists and has proper permissions
- [ ] Set up backup strategy for RAG store
- [ ] Consider using persistent storage for Docker volumes

## Deployment

### 6. Docker Deployment
- [ ] Build Docker image: `docker-compose build`
- [ ] Test locally first: `docker-compose up`
- [ ] Verify health endpoint: `curl http://localhost:8000/api/health`
- [ ] Check logs for errors: `docker-compose logs -f api`

### 7. Performance
- [ ] Set appropriate timeout values
- [ ] Configure max upload size
- [ ] Monitor memory usage (especially with ML models)
- [ ] Implement caching strategy if needed
- [ ] Consider using Gunicorn with multiple workers

### 8. Monitoring
- [ ] Set up application monitoring
- [ ] Configure log aggregation
- [ ] Set up alerts for errors
- [ ] Monitor API response times
- [ ] Track resource usage (CPU, memory, disk)

## Post-Deployment

### 9. Testing
- [ ] Test health endpoint
- [ ] Test chat endpoint with various inputs
- [ ] Test image upload and processing
- [ ] Test voice recording and transcription
- [ ] Test TTS functionality
- [ ] Verify error handling and logging
- [ ] Test rate limits

### 10. Documentation
- [ ] Document deployment process
- [ ] Create runbook for common issues
- [ ] Document API endpoints
- [ ] Update README with production notes

### 11. Backup & Recovery
- [ ] Set up automated backups
- [ ] Test backup restoration
- [ ] Document disaster recovery procedure
- [ ] Plan for zero-downtime updates

## Production Best Practices

### Use Reverse Proxy (Nginx/Traefik)
```nginx
server {
    listen 80;
    server_name mediscope.yourdomain.com;
    
    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name mediscope.yourdomain.com;
    
    ssl_certificate /path/to/cert.pem;
    ssl_certificate_key /path/to/key.pem;
    
    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=10r/s;
    limit_req zone=api burst=20 nodelay;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Timeouts
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }
}
```

### Use Gunicorn for Production
```bash
gunicorn app.main:app \
    --workers 4 \
    --worker-class uvicorn.workers.UvicornWorker \
    --bind 0.0.0.0:8000 \
    --timeout 120 \
    --access-logfile logs/access.log \
    --error-logfile logs/error.log
```

### Environment-Specific Settings

**Development:**
- LOG_LEVEL=DEBUG
- DEMO_MODE=true
- ENABLE_FILE_LOGGING=false

**Staging:**
- LOG_LEVEL=INFO
- DEMO_MODE=false
- ENABLE_FILE_LOGGING=true
- Use staging API keys

**Production:**
- LOG_LEVEL=WARNING
- DEMO_MODE=false
- ENABLE_FILE_LOGGING=true
- Use production API keys
- Strict CORS policy

## Compliance & Legal

### Medical Disclaimer
- [ ] Ensure medical disclaimer is displayed prominently
- [ ] Log all medical advice requests
- [ ] Implement audit trail
- [ ] Review HIPAA compliance requirements (if applicable)
- [ ] Consult legal team for liability concerns

### Data Privacy
- [ ] Review GDPR/privacy requirements
- [ ] Implement data retention policy
- [ ] Allow users to delete their data
- [ ] Document data handling procedures

## Troubleshooting

### Common Issues

**Application won't start:**
- Check `.env` configuration
- Verify all required environment variables
- Check logs for missing dependencies

**LLM not responding:**
- Verify API key is correct
- Check network connectivity
- Review timeout settings
- Check rate limits

**Model loading fails:**
- Ensure sufficient memory
- Verify CUDA drivers (for GPU)
- Check disk space
- Review model compatibility

**Performance issues:**
- Increase worker count
- Add caching layer
- Optimize model loading
- Review timeout settings

## Monitoring Metrics

Track these key metrics:
- Request rate (requests/second)
- Response time (p50, p95, p99)
- Error rate (4xx, 5xx)
- CPU and memory usage
- Disk usage (especially for logs and data)
- API provider costs
- Model inference time

## Scaling Considerations

### Horizontal Scaling
- Use load balancer
- Separate API and ML services
- Consider serverless for LLM calls
- Use managed services for STT/TTS

### Vertical Scaling
- Increase container resources
- Use faster GPUs for vision models
- Optimize model quantization
- Use model caching

## Contact & Support

For production issues:
1. Check logs first
2. Review this checklist
3. Consult documentation
4. Create GitHub issue with details
