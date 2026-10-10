import fs from 'node:fs';
const api=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/ApiClient.java','utf8');
const robot=fs.readFileSync('app/src/main/java/com/profitloop/blueauto/RobotService.java','utf8');
for(const required of ['postControl("heartbeat"','postControl("lease_command"','postControl("network_dashboard"','postControl("command_status"','7_000, 10_000','connection.setUseCaches(false)','finally {','connection.disconnect()']){
  if(!api.includes(required)) throw new Error('control-plane HTTP contract missing: '+required);
}
if(!api.includes('12_000, 18_000')) throw new Error('conservative transaction timeout removed');
for(const required of ['apiRetryAtByProfile','apiFailureCountByProfile','markProfileApiFailure','clearProfileApiFailure','autres SIM non bloquées','Math.min(30_000L']){
  if(!robot.includes(required)) throw new Error('profile transport isolation missing: '+required);
}
if(!robot.includes('JSONObject lease = api.leaseCommand();\n                    clearProfileApiFailure(profileId);')) throw new Error('circuit success reset missing');
if(robot.includes('IDLE_POLL_MS = 3_000')) throw new Error('poll frequency increased instead of isolating faults');
console.log('v2.6.8 control plane: bounded polling HTTP and per-profile transport isolation OK');
