from pathlib import Path
p=Path('app/src/main/assets/app.js')
s=p.read_text()
old="""            var maxBase=Number(capacity.maximum_base_amount||0), rate=Number(capacity.commission_rate_bps||0), maxCommission=Math.floor(maxBase*rate/10000), maxTotal=maxBase+maxCommission;
            showActionError({code:'SOLDE_SUPÉRIEUR_INSUFFISANT',message:'Vous ne pouvez pas commander ce montant. Solde actuellement disponible : '+formatMoney(capacity.available_balance||0)+' FCFA. Avec votre taux '+String(rate/100).replace('.',',')+' %, le montant commandable maximum est '+formatMoney(maxBase)+' FCFA + '+formatMoney(maxCommission)+' FCFA de commission = '+formatMoney(maxTotal)+' FCFA à recevoir. Aucune somme n’est réservée tant que vous n’avez pas confirmé.'});"""
new="""            var rate=Number(capacity.commission_rate_bps||0), maxBase=Number(capacity.maximum_base_amount||0), available=Number(capacity.available_balance||0);
            if(maxBase<=0&&available>0){maxBase=Math.floor(available*10000/(10000+rate));while(maxBase>0&&(maxBase+Math.floor(maxBase*rate/10000))>available){maxBase-=1;}}
            var maxCommission=Math.floor(maxBase*rate/10000), maxTotal=maxBase+maxCommission;
            showActionError({code:'SOLDE_SUPÉRIEUR_INSUFFISANT',message:'Vous ne pouvez pas commander ce montant. Solde actuellement disponible : '+formatMoney(available)+' FCFA. Avec votre taux '+String(rate/100).replace('.',',')+' %, le montant commandable maximum est '+formatMoney(maxBase)+' FCFA + '+formatMoney(maxCommission)+' FCFA de commission = '+formatMoney(maxTotal)+' FCFA à recevoir. Aucune somme n’est réservée tant que vous n’avez pas confirmé : un autre DSM/PoS peut confirmer avant vous et modifier le disponible.'});"""
if old not in s: raise SystemExit('max order UI anchor missing')
p.write_text(s.replace(old,new,1))
