using { /Fortnite.com/Devices }
using { /Fortnite.com/Characters }
using { /Fortnite.com/Playspaces }
using { /Verse.org/Simulation }
using { /UnrealEngine.com/Temporary/Diagnostics }

# 局内经济、军备锻造与基地科技控制器
currency_economy_device := class(creative_device):

    # 经济配置
    @editable StartingGold : int = 500
    @editable Tier2UpgradeCost : int = 1500
    @editable Tier3UpgradeCost : int = 4000
    @editable RepairCost : int = 500
    @editable ShieldUpgradeCost : int = 1000

    # 关联装置
    @editable Tier1Granter : ?item_granter_device = false
    @editable Tier2Granter : ?item_granter_device = false
    @editable Tier3Granter : ?item_granter_device = false
    @editable UpgradeWeaponButton : ?button_device = false
    @editable BuyRepairButton : ?button_device = false
    @editable BuyShieldUpgradeButton : ?button_device = false
    @editable EconomyHud : ?hud_message_device = false
    @editable CoreHealthDevice : ?core_health_device = false

    # 玩家运行时经济与军备追踪
    var PlayerGoldMap : [agent]int = map{}
    var PlayerWeaponTierMap : [agent]int = map{}

    OnBegin<override>()<suspends> : void =
        # 监听锻造台与后勤终端互动事件
        if (UpgradeBtn := UpgradeWeaponButton?):
            UpgradeBtn.InteractedWithEvent.Subscribe(OnPlayerRequestWeaponUpgrade)

        if (RepairBtn := BuyRepairButton?):
            RepairBtn.InteractedWithEvent.Subscribe(OnPlayerRequestCoreRepair)

        if (ShieldBtn := BuyShieldUpgradeButton?):
            ShieldBtn.InteractedWithEvent.Subscribe(OnPlayerRequestShieldUpgrade)

        # 为初始玩家分发基础金币与初始枪械
        InitAllPlayers()
        Print("【军备终端】初始化完成！支持一键合成与基地后勤保障。")

    # 初始化进入游戏的所有特工
    InitAllPlayers() : void =
        AllPlayers := GetPlayspace().GetPlayers()
        for (Player : AllPlayers):
            InitAgent(Player)

    InitAgent<public>(Agent : agent) : void =
        if (not PlayerGoldMap[Agent]):
            if (set PlayerGoldMap[Agent] = StartingGold) {}
            if (set PlayerWeaponTierMap[Agent] = 1) {}
            # 发放初始蓝色武器
            if (Granter := Tier1Granter?):
                Granter.GrantItem(Agent)
            NotifyPlayer(Agent, "【空投补给】已获取初始武器与 500 金币！")

    # 增加金币 (打怪掉落/通关奖励)
    AddGold<public>(Agent : agent, Amount : int) : void =
        Current := GetGold(Agent)
        NewTotal := Current + Amount
        if (set PlayerGoldMap[Agent] = NewTotal):
            NotifyPlayer(Agent, "+{Amount} 金币 (当前储备: {NewTotal})")

    # 扣除金币 (购买门票/强化装备)
    DeductGold<public>(Agent : agent, Amount : int) : logic =
        Current := GetGold(Agent)
        if (Current >= Amount):
            NewTotal := Current - Amount
            if (set PlayerGoldMap[Agent] = NewTotal):
                NotifyPlayer(Agent, "-{Amount} 金币 (剩余储备: {NewTotal})")
                return true
        NotifyPlayer(Agent, "【余额不足】需要 {Amount} 金币，当前仅有 {Current}！")
        return false

    GetGold<public>(Agent : agent) : int =
        if (Gold := PlayerGoldMap[Agent]):
            return Gold
        return 0

    # 玩家申请武器升阶
    OnPlayerRequestWeaponUpgrade(Agent : agent) : void =
        CurrentTier := if (Tier := PlayerWeaponTierMap[Agent]) then Tier else 1

        case (CurrentTier):
            1 =>
                # 升级至 T2 (高爆金色武器)
                if (DeductGold(Agent, Tier2UpgradeCost)?):
                    if (set PlayerWeaponTierMap[Agent] = 2):
                        if (Granter := Tier2Granter?):
                            Granter.GrantItem(Agent)
                        NotifyPlayer(Agent, "【军备质变】武器成功升阶为 T2 高爆机枪！")
            2 =>
                # 升级至 T3 (终极神兵)
                if (DeductGold(Agent, Tier3UpgradeCost)?):
                    if (set PlayerWeaponTierMap[Agent] = 3):
                        if (Granter := Tier3Granter?):
                            Granter.GrantItem(Agent)
                        NotifyPlayer(Agent, "【终极觉醒】已解锁 T3 神兵【雷神之怒】！")
            _ =>
                NotifyPlayer(Agent, "当前武器已达至高级质变等级！")

    # 购买核心紧急维修 (+5000 HP)
    OnPlayerRequestCoreRepair(Agent : agent) : void =
        if (Core := CoreHealthDevice?):
            if (DeductGold(Agent, RepairCost)?):
                Core.RepairCore(5000.0)
                NotifyPlayer(Agent, "【工程指令】已注入纳米自愈凝胶，核心恢复 5,000 生命！")

    # 购买核心护盾扩容 (+2000 MaxShield)
    OnPlayerRequestShieldUpgrade(Agent : agent) : void =
        if (Core := CoreHealthDevice?):
            if (DeductGold(Agent, ShieldUpgradeCost)?):
                Core.UpgradeCoreShield(2000.0)
                NotifyPlayer(Agent, "【科技升级】能量核心护盾上限永久扩容 +2,000！")

    NotifyPlayer(Agent : agent, MessageText : string) : void =
        Print(MessageText)
        if (Hud := EconomyHud?):
            Hud.SetText(StringToMessage(MessageText))
            Hud.Show(Agent)

    StringToMessage<localizes>(Value : string) : message = "{Value}"
