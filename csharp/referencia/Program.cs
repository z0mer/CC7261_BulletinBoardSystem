using System;
using System.Collections.Generic;
using System.Linq;
using System.Threading;
using NetMQ;
using NetMQ.Sockets;
using MessagePack;

namespace ServidorReferencia
{
    public class ServerInfo
    {
        public string Name { get; set; } = string.Empty;
        public int Rank { get; set; }
        public DateTime LastHeartbeat { get; set; }
    }

    public class ServidorReferencia
    {
        private ResponseSocket? repSocket;
        private readonly Dictionary<string, ServerInfo> servers;
        private int nextRank;
        private int logicalClock;
        private readonly object lockObj = new object();

        public ServidorReferencia()
        {
            servers = new Dictionary<string, ServerInfo>();
            nextRank = 1;
            logicalClock = 0;
        }

        private int IncrementClock()
        {
            lock (lockObj)
            {
                logicalClock++;
                return logicalClock;
            }
        }

        private int UpdateClock(int receivedClock)
        {
            lock (lockObj)
            {
                logicalClock = Math.Max(logicalClock, receivedClock) + 1;
                return logicalClock;
            }
        }

        public void Start()
        {
            repSocket = new ResponseSocket();
            repSocket.Bind("tcp://*:5559");

            Console.WriteLine("╔════════════════════════════════════════╗");
            Console.WriteLine("║  Servidor de Referência Iniciado      ║");
            Console.WriteLine("║  Porta: 5559                           ║");
            Console.WriteLine("╚════════════════════════════════════════╝");
            Console.WriteLine();

            // Thread para limpar servidores inativos
            Thread cleanupThread = new Thread(CleanupInactiveServers)
            {
                IsBackground = true
            };
            cleanupThread.Start();

            while (true)
            {
                try
                {
                    byte[] messageBytes = repSocket.ReceiveFrameBytes();
                    var message = MessagePackSerializer.Deserialize<Dictionary<string, object>>(messageBytes);

                    string service = message["service"].ToString() ?? string.Empty;
                    var data = message["data"] as Dictionary<object, object>;

                    if (data == null)
                    {
                        Console.WriteLine("Erro: dados inválidos recebidos");
                        continue;
                    }

                    Dictionary<string, object> response = service switch
                    {
                        "rank" => HandleRank(data),
                        "list" => HandleList(data),
                        "heartbeat" => HandleHeartbeat(data),
                        _ => new Dictionary<string, object>
                        {
                            ["error"] = "Serviço desconhecido"
                        }
                    };

                    byte[] responseBytes = MessagePackSerializer.Serialize(response);
                    repSocket.SendFrame(responseBytes);
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"❌ Erro ao processar mensagem: {ex.Message}");
                }
            }
        }

        private Dictionary<string, object> HandleRank(Dictionary<object, object> data)
        {
            string serverName = data["user"]?.ToString() ?? string.Empty;
            int receivedClock = Convert.ToInt32(data["clock"]);
            UpdateClock(receivedClock);

            lock (lockObj)
            {
                if (!servers.ContainsKey(serverName))
                {
                    servers[serverName] = new ServerInfo
                    {
                        Name = serverName,
                        Rank = nextRank++,
                        LastHeartbeat = DateTime.Now
                    };
                    Console.WriteLine($"✓ Servidor '{serverName}' registrado com rank {servers[serverName].Rank}");
                }
                else
                {
                    servers[serverName].LastHeartbeat = DateTime.Now;
                }

                return new Dictionary<string, object>
                {
                    ["service"] = "rank",
                    ["data"] = new Dictionary<string, object>
                    {
                        ["rank"] = servers[serverName].Rank,
                        ["timestamp"] = DateTimeOffset.Now.ToUnixTimeSeconds(),
                        ["clock"] = IncrementClock()
                    }
                };
            }
        }

        private Dictionary<string, object> HandleList(Dictionary<object, object> data)
        {
            int receivedClock = Convert.ToInt32(data["clock"]);
            UpdateClock(receivedClock);

            lock (lockObj)
            {
                var serverList = servers.Values
                    .Select(s => new Dictionary<string, object>
                    {
                        ["name"] = s.Name,
                        ["rank"] = s.Rank
                    })
                    .ToList();

                Console.WriteLine($"📋 Lista de servidores solicitada ({serverList.Count} servidores)");

                return new Dictionary<string, object>
                {
                    ["service"] = "list",
                    ["data"] = new Dictionary<string, object>
                    {
                        ["list"] = serverList,
                        ["timestamp"] = DateTimeOffset.Now.ToUnixTimeSeconds(),
                        ["clock"] = IncrementClock()
                    }
                };
            }
        }

        private Dictionary<string, object> HandleHeartbeat(Dictionary<object, object> data)
        {
            string serverName = data["user"]?.ToString() ?? string.Empty;
            int receivedClock = Convert.ToInt32(data["clock"]);
            UpdateClock(receivedClock);

            lock (lockObj)
            {
                if (servers.ContainsKey(serverName))
                {
                    servers[serverName].LastHeartbeat = DateTime.Now;
                }

                return new Dictionary<string, object>
                {
                    ["service"] = "heartbeat",
                    ["data"] = new Dictionary<string, object>
                    {
                        ["timestamp"] = DateTimeOffset.Now.ToUnixTimeSeconds(),
                        ["clock"] = IncrementClock()
                    }
                };
            }
        }

        private void CleanupInactiveServers()
        {
            while (true)
            {
                Thread.Sleep(30000); // Verifica a cada 30 segundos

                lock (lockObj)
                {
                    var inactiveServers = servers
                        .Where(kvp => (DateTime.Now - kvp.Value.LastHeartbeat).TotalSeconds > 60)
                        .Select(kvp => kvp.Key)
                        .ToList();

                    foreach (var serverName in inactiveServers)
                    {
                        Console.WriteLine($"⚠️  Removendo servidor inativo: {serverName}");
                        servers.Remove(serverName);
                    }

                    if (inactiveServers.Count > 0)
                    {
                        Console.WriteLine($"📊 Servidores ativos: {servers.Count}");
                    }
                }
            }
        }
    }

    class Program
    {
        static void Main(string[] args)
        {
            Console.WriteLine("Iniciando Servidor de Referência...");
            Console.WriteLine();
            
            var servidor = new ServidorReferencia();
            servidor.Start();
        }
    }
}