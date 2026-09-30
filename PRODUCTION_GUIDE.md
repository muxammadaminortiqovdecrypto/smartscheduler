# Production Deployment Guide

## Environment Setup

### 1. Environment Variables (.env)
```env
SECRET_KEY=<strong-random-secret-key>
DEBUG=False
ALLOWED_HOSTS=yourdomain.com,www.yourdomain.com

# PostgreSQL Database
DATABASE_URL=postgresql://user:password@host:5432/dbname

# Telegram Bot
TELEGRAM_BOT_TOKEN=your_bot_token
```

### 2. PostgreSQL Setup
```bash
# Install PostgreSQL
sudo apt-get install postgresql postgresql-contrib

# Create database
sudo -u postgres psql
CREATE DATABASE smartscheduler;
CREATE USER smartscheduler WITH PASSWORD 'strong_password';
GRANT ALL PRIVILEGES ON DATABASE smartscheduler TO smartscheduler;
\q
```

### 3. Dependencies
```bash
pip install -r requirements.txt
```

### 4. Migrations
```bash
python manage.py makemigrations
python manage.py migrate
```

### 5. Collect Static Files
```bash
python manage.py collectstatic --noinput
```

### 6. Create Superuser
```bash
python manage.py createsuperuser
```

### 7. Gunicorn Setup
```bash
pip install gunicorn
gunicorn smartscheduler.wsgi:application --bind 0.0.0.0:8000
```

### 8. Nginx Configuration
```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location /static/ {
        alias /path/to/static/files/;
    }

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

### 9. Systemd Service (Bot)
```ini
[Unit]
Description=Smart Timetable Bot
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/smartscheduler
ExecStart=/path/to/venv/bin/python bot/main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

### 10. Systemd Service (Web)
```ini
[Unit]
Description=Smart Timetable Web
After=network.target

[Service]
User=www-data
WorkingDirectory=/path/to/smartscheduler
ExecStart=/path/to/venv/bin/gunicorn smartscheduler.wsgi:application --bind 127.0.0.1:8000
Restart=always

[Install]
WantedBy=multi-user.target
```

## Schedule Generation Improvements

### Current Constraints:
1. **Daily Limit**: Maximum 3 lessons per day per teacher
2. **Rest Hours**: 1 rest hour after every 3 consecutive lessons
3. **Seminar After Lecture**: Seminars must be scheduled after lectures
4. **Stavka Limit**: Maximum hours based on teacher's stavka

### Recommendations for Better Schedule:

#### 1. Teacher Stavka Optimization
- **Problem**: Some teachers have low stavka (0.5, 0.75) which limits their weekly hours
- **Solution**: 
  - Increase stavka for teachers with many subjects
  - Balance workload across teachers
  - Example: If a teacher teaches 3 subjects, give them 1.5 stavka (30 hours/week)

#### 2. Room Capacity
- **Problem**: Small rooms may not fit all students
- **Solution**:
  - Add more rooms with higher capacity
  - Match room size to group size
  - Example: KI-210 has 40 students → need room with capacity ≥40

#### 3. Subject Distribution
- **Problem**: Some subjects have too many hours
- **Solution**:
  - Reduce lecture/seminar hours per week
  - Split subjects across multiple teachers
  - Example: Instead of 2 lectures + 2 seminars, use 2 lectures + 1 seminar

#### 4. Time Slot Optimization
- **Problem**: Random shuffle may create gaps
- **Solution**:
  - Prioritize morning slots (1-3 para) for lectures
  - Schedule seminars in afternoon (4-5 para)
  - Avoid scheduling on Friday afternoon (students tired)

#### 5. Group Scheduling
- **Problem**: Groups may have conflicting schedules
- **Solution**:
  - Ensure groups have similar schedules for common subjects
  - Avoid back-to-back classes in different buildings
  - Leave buffer time between classes

#### 6. Teacher Preferences
- **Problem**: Teachers may have preferred days/times
- **Solution**:
  - Add teacher preference fields (preferred_days, preferred_pairs)
  - Respect preferences in scheduling algorithm
  - Allow teachers to block certain time slots

#### 7. OR-Tools Integration (Future)
- **Current**: Backtracking algorithm (slow for large datasets)
- **Recommendation**: 
  - Implement OR-Tools CP-SAT solver
  - Define constraints as mathematical model
  - Optimize for teacher satisfaction and student convenience
  - Expected speedup: 10-100x faster

## Monitoring & Maintenance

### 1. Database Backups
```bash
# Daily backup
pg_dump -U smartscheduler smartscheduler > backup_$(date +%Y%m%d).sql
```

### 2. Log Monitoring
- Check Django logs for errors
- Monitor bot logs for API issues
- Track schedule generation failures

### 3. Performance Monitoring
- Monitor database query times
- Track bot response times
- Monitor web server load

### 4. Security
- Keep dependencies updated
- Use strong SECRET_KEY
- Enable HTTPS (Let's Encrypt)
- Regular security audits

## Scaling Considerations

### 1. Database
- Use connection pooling
- Add read replicas for high traffic
- Consider Redis for caching

### 2. Bot
- Use webhook instead of polling for better performance
- Add rate limiting
- Implement message queue for heavy operations

### 3. Web
- Use CDN for static files
- Implement caching (Redis)
- Load balancer for multiple web servers

## Troubleshooting

### Bot Conflict Error
- **Error**: "Conflict: terminated by other getUpdates request"
- **Solution**: Stop all bot instances, ensure only one is running

### Database Connection Error
- **Error**: "could not connect to server"
- **Solution**: Check PostgreSQL is running, credentials are correct

### Schedule Generation Failure
- **Error**: "Only X/Y hours placed"
- **Solution**: 
  - Increase teacher stavka
  - Add more rooms
  - Reduce subject hours
  - Check for conflicting constraints
