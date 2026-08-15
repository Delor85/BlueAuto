from pathlib import Path

p = Path('app/src/main/java/com/profitloop/blueauto/RobotService.java')
s = p.read_text()
old = '''                } catch (Exception profileError) {
                    long retryAt = markProfileApiFailure(profileId);
                    long seconds = Math.max(1L, (retryAt - System.currentTimeMillis() + 999L) / 1000L);'''
new = '''                } catch (Exception profileError) {
                    long failureRetryAt = markProfileApiFailure(profileId);
                    long seconds = Math.max(1L, (failureRetryAt - System.currentTimeMillis() + 999L) / 1000L);'''
if old not in s:
    raise SystemExit('control-plane retry variable anchor missing')
p.write_text(s.replace(old, new, 1))
