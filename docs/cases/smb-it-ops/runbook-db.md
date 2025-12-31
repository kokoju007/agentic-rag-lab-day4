# Database Backup/Restore Runbook

## Backup Verification Checklist
DB 백업 검증 절차: 최신 백업 성공 여부, 체크섬 확인, 보존 정책 확인, 기록 남기기
1. Confirm latest backup job status is "success" in the scheduler.
2. Verify backup file size and checksum against the previous run.
3. Ensure retention policy keeps at least 7 daily and 4 weekly backups.
4. Record the backup timestamp in the incident notes.

## Restore Drill Checklist
1. Restore the latest backup to a staging environment.
2. Run a read-only smoke test (connect, list tables, sample query).
3. Compare row counts for critical tables.
4. Record restore duration and any warnings.

## Monitoring Signals
- Backup job failure alert
- Storage threshold warning
- Replication lag above 5 minutes

## Incident Notes Template
- Impact: (service name, customer impact)
- Timeline: (start, detected, mitigated)
- Actions: (steps taken, results)
- Next steps: (follow-up tasks, owner)
