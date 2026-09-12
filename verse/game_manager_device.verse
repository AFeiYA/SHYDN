using { /Fortnite.com/Devices }
using { /Fortnite.com/Characters }
using { /Fortnite.com/Playspaces }
using { /Verse.org/Simulation }
using { /UnrealEngine.com/Temporary/Diagnostics }

# 战局顶层状态机
game_state := enum:
    Initializing
    HeroSelection       # 英雄神殿选人阶段：不刷怪，等待特工选定职业
    PreMatchCountdown   # 选人完毕后 10 秒倒计时：前往前线哨位迎敌
    WaveInProgress
    WaveIntermission
    Defeat
    Victory

# 《零界防线：核心守卫》全局主脑控制器
game_manager_device := class(creative_device):

    # 关联子系统控制器
    @editable CoreHealthDevice : ?core_health_device = false
    @editable WaveControllerDevice : ?wave_controller_device = false
    @editable EconomyDevice : ?currency_economy_device = false
    @editable HeroRpgDevice : ?hero_rpg_device = false
    @editable EndGameDevice : ?end_game_device = false
    @editable GlobalHudMessage : ?hud_message_device = false

    # 初始准备时间
    @editable InitialCountdownSeconds : float = 10.0

    # 运行状态
    var CurrentState : game_state = game_state.Initializing

    OnBegin<override>()<suspends> : void =
        Print("【HERA 主脑】零界防线系统自检完成，启动核心协议...")
        
        # 监听玩家加入
        GetPlayspace().PlayerAddedEvent().Subscribe(OnPlayerJoined)
        for (ExistingPlayer : GetPlayspace().GetPlayers()):
            OnPlayerJoined(ExistingPlayer)

        # 启动事件监听协程
        spawn{ ListenCoreDestroyed() }
        spawn{ ListenWaveStarted() }
        spawn{ ListenWaveCleared() }
        spawn{ ListenAllWavesCleared() }

        # 启动战局主导流程
        spawn{ StartMatchFlow() }

    # 玩家动态加入
    OnPlayerJoined(Player : player) : void =
        if (Economy := EconomyDevice?):
            Economy.InitAgent(Player)
        Print("【HERA】特工接入防线，等待英雄就绪。")

    # 战局主流程: [1. 英雄选取] -> [2. 准备倒计时] -> [3. 波次循环]
    StartMatchFlow()<suspends> : void =
        set CurrentState = game_state.HeroSelection
        BroadcastLore("【HERA】特工已降临英雄神殿！走向看台按下互动，选择你的本命英雄！")

        # 挂起等待玩家选取英雄 (或 60 秒兜底防挂机)
        if (HeroDevice := HeroRpgDevice?):
            race:
                block:
                    HeroDevice.AllPlayersReadyEvent.Await()
                    Print("【HERA】全员英雄选定，整装待发！")
                block:
                    Sleep(60.0)
                    Print("【HERA】选人阶段结束，防线警报拉响！")
        else:
            Sleep(5.0)

        # 进入出击倒计时
        set CurrentState = game_state.PreMatchCountdown
        BroadcastLore("【HERA】英雄已入驻哨位！四向虚空裂隙将在 10 秒后爆发！拔枪迎战！")
        Sleep(InitialCountdownSeconds)

        # 移交控制权给波次调度器
        if (WaveCtrl := WaveControllerDevice?):
            set CurrentState = game_state.WaveInProgress
            WaveCtrl.StartWaveSequence()

    # 波次开始回调
    OnWaveStarted(WaveIndex : int) : void =
        set CurrentState = game_state.WaveInProgress
        BroadcastLore("【HERA】第 {WaveIndex} 阶段虚空共振开始！敌人正从东、南、西、北四面逼近！各哨位坚守！")

    # 波次防守成功回调（全员通关分红）
    OnWaveCleared(WaveIndex : int) : void =
        set CurrentState = game_state.WaveIntermission
        BonusGold := 200 + (WaveIndex * 25)
        
        AllPlayers := GetPlayspace().GetPlayers()
        for (Player : AllPlayers):
            if (Economy := EconomyDevice?):
                Economy.AddGold(Player, BonusGold)

        BroadcastLore("【HERA】第 {WaveIndex} 波已抵御！全员发放战术分红 +{BonusGold} 金币！")

    # 核心摧毁失败回调
    OnCoreDestroyed() : void =
        set CurrentState = game_state.Defeat
        BroadcastLore("【HERA】零号矩阵已瓦解……防线彻底沦陷。")
        if (EndGame := EndGameDevice?):
            AllPlayers := GetPlayspace().GetPlayers()
            if (FirstPlayer := AllPlayers[0]):
                EndGame.Activate(FirstPlayer)

    # 全部通关终极大胜
    OnAllWavesCleared() : void =
        set CurrentState = game_state.Victory
        BroadcastLore("【HERA】虚空裂隙已彻底闭合！净化脉冲激活！今晚，地表重归人类！")
        if (EndGame := EndGameDevice?):
            AllPlayers := GetPlayspace().GetPlayers()
            if (FirstPlayer := AllPlayers[0]):
                EndGame.Activate(FirstPlayer)

    # 协程监听函数
    ListenCoreDestroyed()<suspends> : void =
        if (Core := CoreHealthDevice?):
            Core.CoreDestroyedEvent.Await()
            OnCoreDestroyed()

    ListenWaveStarted()<suspends> : void =
        if (WaveCtrl := WaveControllerDevice?):
            loop:
                WaveIndex := WaveCtrl.WaveStartedEvent.Await()
                OnWaveStarted(WaveIndex)

    ListenWaveCleared()<suspends> : void =
        if (WaveCtrl := WaveControllerDevice?):
            loop:
                WaveIndex := WaveCtrl.WaveClearedEvent.Await()
                OnWaveCleared(WaveIndex)

    ListenAllWavesCleared()<suspends> : void =
        if (WaveCtrl := WaveControllerDevice?):
            WaveCtrl.AllWavesCompletedEvent.Await()
            OnAllWavesCleared()

    BroadcastLore(Text : string) : void =
        Print(Text)
        if (Hud := GlobalHudMessage?):
            Hud.SetText(StringToMessage(Text))
            Hud.Show()

    StringToMessage<localizes>(Value : string) : message = "{Value}"
