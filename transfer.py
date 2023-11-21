import threading
from web3 import Web3
import requests
import time
import random
from decimal import Decimal

POLYGON_API_TOKEN = 'you_api_polygon'
MINIMUM_MATIC_AMOUNT = 0.5 # количество матика для минималньой отправки в транзакции
MAX_WAIT_TIME = 120 # время проверки транзакции на отправку
POLYGON_RPC = 'https://polygon-rpc.com' # rpc polygon

def get_initial_balance(private_key):
   w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))
   account = w3.eth.account.from_key(private_key)
   balance = w3.eth.get_balance(account.address)
   print(f"Начальный баланс кошелька {account.address}: {w3.from_wei(balance, 'ether')} Matic")

def send_transaction(private_key, to_address, gas_price, minimum_balance, minimum_matic_amount):
   w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))
   account = w3.eth.account.from_key(private_key)
   
   nonce = w3.eth.get_transaction_count(account.address)
   nonce += 1
 
   balance = w3.eth.get_balance(account.address)
   u = w3.from_wei(balance, 'ether')
   p = Decimal(minimum_balance)  # Преобразовываем 'float' в 'decimal.Decimal'
   t = u - p

   if balance < w3.to_wei(t, 'ether'):
       print(f"Недостаточно средств для отправки транзакции с кошелька {account.address}")
       return

   if t < minimum_matic_amount:
       print(f"Объем отправляемого Matic меньше {minimum_matic_amount}. Транзакция отменена.")
       return

   nonce = w3.eth.get_transaction_count(account.address)
   gas_limit = 21000
   gas_price = max(gas_price, get_gas_price())
    
   print(f"Отправляется {t} Matic с кошелька {account.address} на адрес {to_address}")
 
   txn = {
       'nonce': nonce,
       'to': to_address,
       'value': w3.to_wei(t, 'ether'),
       'gas': gas_limit,
       'gasPrice': gas_price,
       'chainId': 137  
   }

   remaining_balance = w3.eth.get_balance(account.address) - w3.to_wei(t, 'ether')
   remaining_matic = w3.from_wei(remaining_balance, 'ether')

   if remaining_matic < minimum_balance:
       print(f"Оставшийся баланс меньше минимального значения {minimum_balance} Matic. Транзакция отменена.")
       return

   signed_txn = w3.eth.account.sign_transaction(txn, private_key)
   txn_hash = w3.eth.send_raw_transaction(signed_txn.rawTransaction).hex()
 
   print(f"Отправлена транзакция с кошелька {account.address} на адрес {to_address}, хеш: {txn_hash}")

   start_time = time.time()
   while time.time() - start_time < MAX_WAIT_TIME:
       time.sleep(40) # Задержка перед проверкой статуса транзакции
       txn_receipt = w3.eth.get_transaction_receipt(txn_hash)
       if get_transaction_status(txn_hash):
           print(f"Транзакция {txn_hash} успешно подтверждена.")
           break
       else:
           print(f"Ожидание подтверждения транзакции {txn_hash}...")
           time.sleep(5)

   return txn_hash

def get_transaction_status(txn_hash):
   w3 = Web3(Web3.HTTPProvider(POLYGON_RPC))
   txn_receipt = w3.eth.get_transaction_receipt(txn_hash)
   return txn_receipt['status'] == 1 if txn_receipt else False

def get_gas_price():
 headers = {'Authorization': f'Bearer {POLYGON_API_TOKEN}'}
 try:
     response = requests.get('https://gasstation.polygon.technology/v2', headers=headers)
     response.raise_for_status()
     gas_price_dict = response.json()
     if isinstance(gas_price_dict['fast'], dict) and 'maxFee' in gas_price_dict['fast']:
         return int(gas_price_dict['fast']['maxFee'])
     else:
         print(f"Некорректные данные о стоимости газа: {gas_price_dict['fast']}")
         return 0 # Возвращаем 0 в случае ошибки
 except requests.exceptions.RequestException as e:
     print(f"Ошибка при получении стоимости газа: {e}")
     return 0 # Возвращаем 0 в случае ошибки

def read_from_file(filename):
   with open(filename, 'r') as f:
       return [line.strip() for line in f.readlines()]

def main():
  private_keys = read_from_file('accs.txt')
  to_addresses = read_from_file('send.txt')

  threads = int(input('Введите количество потоков (от 1 до 5): '))

  MINIMUM_BALANCES = [round(random.uniform(1.0, 1.2), 3) for _ in range(len(private_keys))] # количество матика остающегося на кошелька, ((от, до) шаг 3 - 0,001)

  for i in range(min(threads, len(private_keys))):
      private_key = private_keys[i]
      to_address = to_addresses[i]
      gas_price = get_gas_price()

      get_initial_balance(private_key)
      threading.Thread(target=send_transaction, args=(private_key, to_address, gas_price, MINIMUM_BALANCES[i], MINIMUM_MATIC_AMOUNT)).start()

if __name__ == '__main__':
   main()
