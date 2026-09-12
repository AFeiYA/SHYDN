using { /Fortnite.com/Devices }
using { /Fortnite.com/Characters }
using { /Fortnite.com/Playspaces }
using { /Verse.org/Simulation }
using { /UnrealEngine.com/Temporary/Diagnostics }

# 练功房 / 挑战副本折跃门控制器
teleport_gate_device := class(creative_device):

    # 门票与配置
    @editable RoomName : string = "初级练功房"
    @editable TicketCost : int = 100
    @editable MaxDurationSeconds : float = 45.0

    # 关联装置
    @editable EnterTrigger : ?button_device = false
    @editable EarlyExitTrigger : ?button_device = false
    @editable FarmRoomTeleporter : ?teleporter_device = false
    @editable BaseReturnTeleporter : ?teleporter_device = false
    @editable TimerHud : ?hud_message_device = false
    @editable CoreHealthDevice : ?core_health_device = false

    # 房内活跃玩家追踪 (用于独立倒计时与安全清理)
    var ActivePlayersInRoom : [agent]logic = map{}

    OnBegin<override>()<suspends> : void =
        if (Btn := EnterTrigger?):
            Btn.InteractedWithEvent.Subscribe(OnPlayerRequestEnter)

        if (ExitBtn := EarlyExitTrigger?):
            ExitBtn.InteractedWithEvent.Subscribe(OnPlayerRequestEarlyExit)

        # 监听核心濒死事件
        spawn{ ListenCoreEmergencyAlert() }

        Print("【折跃门-{RoomName}】初始化完毕，限时: {MaxDurationSeconds}秒，门票: {TicketCost}")

    # 玩家申请入场
    OnPlayerRequestEnter(Agent : agent) : void =
        # 检查是否已在房内
        if (ActivePlayersInRoom[Agent] = true):
            Print("玩家已在练功房内！")
            return

        # 登记玩家并折跃
        if (set ActivePlayersInRoom[Agent] = true):
            Print("【折跃门】特工通过验证，扣除门票 {TicketCost}，折跃至 {RoomName}！")
            if (TeleportToRoom := FarmRoomTeleporter?):
                TeleportToRoom.Teleport(Agent)

            # 启动 45 秒强制计时与生命周期协程
            spawn{ RunPlayerSessionTimer(Agent) }

    # 45 秒倒计时与抢断状态机
    RunPlayerSessionTimer(Agent : agent)<suspends> : void =
        race:
            block:
                # 倒计时 45 秒
                Sleep(MaxDurationSeconds)
                Print("【时间耗尽】特工在 {RoomName} 的时间已达上限，执行强制回传！")
                RecallPlayer(Agent, "时间耗尽！强制折跃回主基地！")

            block:
                # 监听该玩家是否主动离开
                AwaitPlayerExit(Agent)

    # 强制将玩家传回主基地
    RecallPlayer(Agent : agent, Reason : string) : void =
        if (ActivePlayersInRoom[Agent] = true):
            # 移除登记
            var NewMap : [agent]logic = map{}
            for (Key -> Val : ActivePlayersInRoom, Key <> Agent):
                if (set NewMap[Key] = Val) {}
            set ActivePlayersInRoom = NewMap

            # 传回主基地
            if (ReturnTeleporter := BaseReturnTeleporter?):
                ReturnTeleporter.Teleport(Agent)

            if (Hud := TimerHud?):
                Hud.SetText(StringToMessage(Reason))
                Hud.Show(Agent)

    # 玩家主动申请提前离开
    OnPlayerRequestEarlyExit(Agent : agent) : void =
        if (ActivePlayersInRoom[Agent] = true):
            RecallPlayer(Agent, "主动撤离练功房，返回主防线。")

    # 协程：等待玩家被移出活跃名单
    AwaitPlayerExit(Agent : agent)<suspends> : void =
        loop:
            Sleep(1.0)
            if (not ActivePlayersInRoom[Agent]):
                break

    # 核心陷入红色绝境时触发紧急提示
    OnCoreEmergencyAlert() : void =
        for (Agent -> IsActive : ActivePlayersInRoom):
            if (IsActive = true):
                if (Hud := TimerHud?):
                    Hud.SetText(StringToMessage("【绝境警报】能量核心即将崩溃！请立刻撤离回防！"))
                    Hud.Show(Agent)

    ListenCoreEmergencyAlert()<suspends> : void =
        if (Core := CoreHealthDevice?):
            loop:
                Core.EmergencyAlertEvent.Await()
                OnCoreEmergencyAlert()

    StringToMessage<localizes>(Value : string) : message = "{Value}"
